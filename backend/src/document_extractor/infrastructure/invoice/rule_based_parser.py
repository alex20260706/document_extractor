"""Deterministic parsing rules for Spanish and English invoices."""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from document_extractor.domain.common.enums import (
    ContentAcquisitionMethod,
    DataExtractionMethod,
)
from document_extractor.domain.common.models import ExtractedField, FieldScalar
from document_extractor.domain.invoice.assessment import (
    assess_invoice,
    invoice_status,
    invoice_warnings,
)
from document_extractor.domain.invoice.models import (
    InvoiceData,
    InvoiceExtractionResult,
    InvoiceLine,
    Party,
)

_FIELD_LABELS = {
    "invoice_number": "Invoice number",
    "issue_date": "Issue date",
    "issuer_name": "Issuer",
    "issuer_tax_id": "Issuer tax ID",
    "receiver_name": "Receiver",
    "receiver_tax_id": "Receiver tax ID",
    "taxable_base": "Taxable amount",
    "tax_amount": "Tax amount",
    "total_amount": "Total",
    "currency": "Currency",
}

_AMOUNT = (
    r"(?:[-+]?\s*\d(?:[\d.,'’ ]*\d)?|"
    r"\(\s*\d(?:[\d.,'’ ]*\d)?\s*\))"
)
_COLUMN_NUMBER = r"[-+]?\d(?:[\d.,'’]*\d)?"
_CURRENCY = r"(?:EUR|USD|GBP|\u20ac|\$|\u00a3)"
_DATE = (
    r"(?:\d{4}\s*-\s*\d{1,2}\s*-\s*\d{1,2}|"
    r"\d{1,2}\s*[./-]\s*\d{1,2}\s*[./-]\s*\d{2,4})"
)
_VALUE_END = r"(?=$|[ \t\n.;,)])"


class RuleBasedInvoiceParser:
    """Extract invoice data with deterministic, explainable rules."""

    # Each field maps ordered regex alternatives to its base confidence.
    _field_patterns = {
        "invoice_number": (
            (
                r"\b(?:factura|invoice)\s*"
                r"(?:n(?:[u\u00fa]m(?:ero)?)?\.?|"
                r"n[\u00ba\u00b0o]\.?|no\.?|number|#|ref\.?)?"
                r"\s*[:\-]?\s*"
                r"(?P<value>(?=[A-Z0-9./_-]*\d)"
                r"[A-Z0-9][A-Z0-9./_-]{1,39})\b",
                r"\b(?:n(?:[u\u00fa]m(?:ero)?)?\.?|"
                r"n[\u00ba\u00b0o]\.?|no\.?|number|#)"
                r"\s*(?:de\s+)?(?:factura|invoice)\s*[:\-]?\s*"
                r"(?P<value>(?=[A-Z0-9./_-]*\d)"
                r"[A-Z0-9][A-Z0-9./_-]{1,39})\b",
            ),
            0.92,
        ),
        "issue_date": (
            (
                rf"\b(?:fecha(?:\s+de)?\s+(?:emisi[o\u00f3]n|factura)|"
                rf"emitida\s+el|issue\s+date|invoice\s+date|"
                rf"date\s+of\s+issue)\s*[:\-]?\s*"
                rf"(?P<value>{_DATE})\b",
                rf"\bfecha\s*[:\-]\s*(?P<value>{_DATE})\b",
            ),
            0.9,
        ),
        "issuer_name": (
            (
                r"^(?:emisor|proveedor|vendedor|supplier|"
                r"raz[o\u00f3]n\s+social(?:\s+emisor)?)\s*[:\-]\s*"
                r"(?P<value>[^\n]{2,100})$",
            ),
            0.82,
        ),
        "receiver_name": (
            (
                r"^(?:receptor|cliente|comprador|customer|bill\s+to|"
                r"facturar\s+a|destinatario)\s*[:\-]\s*"
                r"(?P<value>[^\n]{2,100})$",
            ),
            0.82,
        ),
        "taxable_base": (
            (
                rf"\b(?:base\s+imponible|subtotal|importe\s+neto|"
                rf"net\s+amount)"
                rf"\s*[:\-]?\s*(?:{_CURRENCY}\s*)?"
                rf"(?P<value>{_AMOUNT})(?:\s*{_CURRENCY})?{_VALUE_END}",
            ),
            0.9,
        ),
        "tax_amount": (
            (
                rf"\b(?:cuota\s+(?:de\s+)?iva|"
                rf"importe\s+(?:de\s+)?iva|"
                rf"iva|vat)(?:\s*\(?\d{{1,2}}(?:[.,]\d+)?\s*%\)?)?"
                rf"\s*[:\-]?\s*(?:{_CURRENCY}\s*)?"
                rf"(?P<value>{_AMOUNT})(?:\s*{_CURRENCY})?{_VALUE_END}",
            ),
            0.86,
        ),
        "total_amount": (
            (
                rf"\b(?:total\s+a\s+pagar|importe\s+total|total\s+factura|"
                rf"grand\s+total|invoice\s+total|total)"
                rf"\s*[:\-]?\s*(?:{_CURRENCY}\s*)?"
                rf"(?P<value>{_AMOUNT})(?:\s*{_CURRENCY})?{_VALUE_END}",
            ),
            0.95,
        ),
    }

    _tax_id_pattern = re.compile(
        r"(?<!\w)(?:ES[ \t-]*)?(?:"
        r"[ABCDEFGHJNPQRSUVW](?:[ \t-]*\d){7}[ \t-]*[0-9A-J]|"
        r"\d(?:[ \t-]*\d){7}[ \t-]*[A-Z]|"
        r"[XYZ](?:[ \t-]*\d){7}[ \t-]*[A-Z])(?!\w)",
        re.IGNORECASE,
    )

    # Product rows require description, quantity and amount columns.
    _line_pattern = re.compile(
        rf"^(?P<description>\D.*?\S)\s+"
        rf"(?P<quantity>\d+(?:[.,]\d+)?)\s*(?:x\s*)?"
        rf"(?P<unit_price>{_COLUMN_NUMBER})\s*(?:{_CURRENCY})?\s+"
        rf"(?:\(?\d+(?:[.,]\d+)?\s*%\)?\s+)?"
        rf"(?P<line_total>{_COLUMN_NUMBER})\s*(?:{_CURRENCY})?$",
        re.IGNORECASE,
    )
    _currency_patterns = (
        (r"(?:\u20ac|\bEUR\b)", "EUR"),
        (r"(?:\$|\bUSD\b)", "USD"),
        (r"(?:\u00a3|\bGBP\b)", "GBP"),
    )

    def parse(
        self,
        text: str,
        acquisition_method: ContentAcquisitionMethod = (
            ContentAcquisitionMethod.EMBEDDED_TEXT
        ),
    ) -> InvoiceExtractionResult:
        """Return normalized invoice data and review warnings.

        Args:
            text: The text to parse.
            acquisition_method: The method used to acquire the content.

        Returns:
            The normalized invoice data and review warnings.
        """

        normalized = self._normalize(text)
        fields = self._empty_fields()
        matches: dict[str, re.Match[str]] = {}

        for key, (patterns, confidence) in self._field_patterns.items():
            match = self._first_match(patterns, normalized)
            if not match:
                continue

            value = self._convert_value(key, match.group("value"))
            if value is None:
                continue

            fields[key] = ExtractedField(
                label=_FIELD_LABELS[key],
                value=value,
                confidence=confidence,
                extraction_method=DataExtractionMethod.RULE_BASED,
            )
            matches[key] = match

        self._assign_tax_ids(normalized, fields, matches)
        self._assign_currency(normalized, fields)

        line_items = tuple[InvoiceLine, ...](self._parse_lines(normalized))
        data = self._build_invoice_data(fields, line_items)
        assessment = assess_invoice(data)

        return InvoiceExtractionResult(
            status=invoice_status(data, assessment),
            data=data,
            acquisition_method=acquisition_method,
            extraction_method=DataExtractionMethod.RULE_BASED,
            warnings=invoice_warnings(data, assessment),
        )

    @staticmethod
    def _empty_fields() -> dict[str, ExtractedField]:
        """Create every expected field with an empty value.

        Returns:
            A dictionary with the expected fields
            and their empty values.
        """

        return {
            key: ExtractedField(label=label)
            for key, label in _FIELD_LABELS.items()
        }

    @staticmethod
    def _first_match(
        patterns: tuple[str, ...],
        text: str,
    ) -> re.Match[str] | None:
        """Return the first matching alternative.

        Args:
            patterns: The patterns to search for.
            text: The text to search in.

        Returns:
            The first matching alternative or None if no match is found.
        """

        for pattern in patterns:
            if match := re.search(
                pattern,
                text,
                flags=re.IGNORECASE | re.MULTILINE,
            ):
                return match
        return None

    @classmethod
    def _convert_value(
        cls,
        key: str,
        raw_value: str,
    ) -> FieldScalar | None:
        """Convert a regex value into its domain representation.

        Args:
            key: The key of the field.
            raw_value: The raw value to convert.

        Returns:
            The converted value or None if the value is not valid.
        """

        match key:
            case "taxable_base" | "tax_amount" | "total_amount":
                return cls._money(raw_value)
            case "issue_date":
                return cls._date(raw_value)
            case "issuer_name" | "receiver_name":
                return cls._clean_party_name(raw_value)
            case _:
                return raw_value.strip()

    @classmethod
    def _assign_tax_ids(
        cls,
        text: str,
        fields: dict[str, ExtractedField],
        matches: dict[str, re.Match[str]],
    ) -> None:
        """Associate tax identifiers with the nearest named party.

        Args:
            text: The text to search in.
            fields: The fields to assign the tax ids to.
            matches: The matches to search for.
        """

        used: set[str] = set()
        for party in ("issuer", "receiver"):
            match = matches.get(f"{party}_name")
            other_party = "receiver" if party == "issuer" else "issuer"
            other_match = matches.get(f"{other_party}_name")
            stop = (
                other_match.start()
                if match and other_match and other_match.start() > match.end()
                else None
            )
            tax_id = cls._tax_id_near(match, text, stop) if match else None
            if tax_id:
                used.add(tax_id)
                fields[f"{party}_tax_id"] = ExtractedField(
                    label=_FIELD_LABELS[f"{party}_tax_id"],
                    value=tax_id,
                    confidence=0.82,
                    extraction_method=DataExtractionMethod.RULE_BASED,
                )

        # Unmatched IDs fall back to document order at low confidence.
        remaining = [
            cls._normalize_tax_id(match.group())
            for match in cls._tax_id_pattern.finditer(text)
            if cls._normalize_tax_id(match.group()) not in used
        ]
        remaining = list(dict.fromkeys(remaining))
        for party in ("issuer", "receiver"):
            key = f"{party}_tax_id"
            if fields[key].missing and remaining:
                fields[key] = ExtractedField(
                    label=_FIELD_LABELS[key],
                    value=remaining.pop(0),
                    confidence=0.5,
                    extraction_method=DataExtractionMethod.RULE_BASED,
                )

    @classmethod
    def _tax_id_near(
        cls,
        party_match: re.Match[str],
        text: str,
        stop: int | None,
    ) -> str | None:
        """Find a tax identifier on or shortly after a party line.

        Args:
            party_match: The match for the party.
            text: The text to search in.
            stop: The position to stop searching at.

        Returns:
            The tax identifier or None if no match is found.
        """

        same_line = party_match.group(0)
        if match := cls._tax_id_pattern.search(same_line):
            return cls._normalize_tax_id(match.group())

        window_end = min(party_match.end() + 180, stop or len(text))
        window = text[party_match.end() : window_end]
        if match := cls._tax_id_pattern.search(window):
            return cls._normalize_tax_id(match.group())
        return None

    @classmethod
    def _clean_party_name(
        cls,
        value: str,
    ) -> str | None:
        """Remove identifiers and punctuation from a party name.

        Args:
            value: The value to clean.

        Returns:
            The cleaned value or None if the value is not valid.
        """

        cleaned = cls._tax_id_pattern.sub("", value)
        cleaned = cleaned.strip(" :-|,")
        return cleaned or None

    @staticmethod
    def _normalize_tax_id(value: str) -> str:
        """Remove separators and capitalize a tax identifier.

        Args:
            value: The value to normalize.

        Returns:
            The normalized value.
        """

        return re.sub(r"[\s-]", "", value).upper()

    @classmethod
    def _assign_currency(
        cls,
        text: str,
        fields: dict[str, ExtractedField],
    ) -> None:
        """Detect the first supported currency symbol or ISO code.

        Args:
            text: The text to search in.
            fields: The fields to assign the currency to.
        """

        for pattern, currency in cls._currency_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                fields["currency"] = ExtractedField(
                    label=_FIELD_LABELS["currency"],
                    value=currency,
                    confidence=0.92,
                    extraction_method=DataExtractionMethod.RULE_BASED,
                )
                return

    @classmethod
    def _parse_lines(cls, text: str) -> list[InvoiceLine]:
        """Extract description, quantity, price and total rows.

        Args:
            text: The text to search in.

        Returns:
            A list of InvoiceLine objects.
        """

        items: list[InvoiceLine] = []
        for raw_line in text.splitlines():
            match = cls._line_pattern.match(raw_line.strip())
            if not match:
                continue

            quantity = cls._money(match.group("quantity"))
            unit_price = cls._money(match.group("unit_price"))
            line_total = cls._money(match.group("line_total"))
            if quantity is None or unit_price is None or line_total is None:
                continue

            expected_total = quantity * unit_price
            # Keep inconsistent rows for review at lower confidence.
            confidence = (
                0.84
                if abs(expected_total - line_total) <= Decimal("0.02")
                else 0.58
            )
            items.append(
                InvoiceLine(
                    description=match.group("description").strip(),
                    quantity=quantity,
                    unit_price=unit_price,
                    line_total=line_total,
                    confidence=confidence,
                    extraction_method=DataExtractionMethod.RULE_BASED,
                )
            )
        return items

    @staticmethod
    def _build_invoice_data(
        fields: dict[str, ExtractedField],
        line_items: tuple[InvoiceLine, ...],
    ) -> InvoiceData:
        """Build the typed invoice model from the extracted fields.

        Args:
            fields: The fields to build the invoice data from.
            line_items: The line items to build the invoice data from.

        Returns:
            The built invoice data.
        """

        return InvoiceData(
            invoice_number=fields["invoice_number"],
            issue_date=fields["issue_date"],
            issuer=Party(
                name=fields["issuer_name"],
                tax_id=fields["issuer_tax_id"],
            ),
            receiver=Party(
                name=fields["receiver_name"],
                tax_id=fields["receiver_tax_id"],
            ),
            taxable_base=fields["taxable_base"],
            tax_amount=fields["tax_amount"],
            total_amount=fields["total_amount"],
            currency=fields["currency"],
            line_items=line_items,
        )

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize spaces while preserving line breaks.

        Args:
            text: The text to normalize.

        Returns:
            The normalized text.
        """

        lines = (
            re.sub(r"[ \t\u00a0]+", " ", line).strip()
            for line in text.replace("\r\n", "\n")
            .replace("\r", "\n")
            .split("\n")
        )
        return "\n".join(line for line in lines if line)

    @staticmethod
    def _money(value: str) -> Decimal | None:
        """Parse European and English decimal/thousands separators.

        Args:
            value: The value to parse.

        Returns:
            The parsed value or None if the value is not valid.
        """

        compact = re.sub(
            r"(?:EUR|USD|GBP|\u20ac|\$|\u00a3|\s|'|’|\u00a0)",
            "",
            value,
        )
        if not compact:
            return None

        negative = compact.startswith("-") or (
            compact.startswith("(") and compact.endswith(")")
        )
        compact = compact.strip("+-()")

        if "," in compact and "." in compact:
            # With both symbols, the rightmost one is the decimal mark.
            decimal_separator = (
                "," if compact.rfind(",") > compact.rfind(".") else "."
            )
            thousands_separator = "." if decimal_separator == "," else ","
            compact = compact.replace(thousands_separator, "")
            compact = compact.replace(decimal_separator, ".")
        elif separator := (
            "," if "," in compact else "." if "." in compact else None
        ):
            groups = compact.split(separator)
            # Repetition or a three-digit suffix denotes grouping.
            if len(groups) > 2 or len(groups[-1]) == 3:
                compact = "".join(groups)
            else:
                compact = ".".join(groups)

        try:
            amount = Decimal(compact)
            return -amount if negative else amount
        except InvalidOperation:
            return None

    @staticmethod
    def _date(value: str) -> date | None:
        """Parse common Spanish and ISO invoice date formats.

        Args:
            value: The value to parse.

        Returns:
            The parsed value or None if the value is not valid.
        """

        value = re.sub(r"\s+", "", value)

        formats = (
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d.%m.%Y",
            "%d/%m/%y",
            "%d-%m-%y",
            "%d.%m.%y",
            "%Y-%m-%d",
        )
        for pattern in formats:
            try:
                return datetime.strptime(value, pattern).date()
            except ValueError:
                continue
        return None
