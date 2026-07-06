"""Deterministic parsing rules for bilingual purchase orders."""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from document_extractor.domain.common.enums import (
    ContentAcquisitionMethod,
    DataExtractionMethod,
)
from document_extractor.domain.common.models import ExtractedField, FieldScalar
from document_extractor.domain.purchase_order.assessment import (
    assess_purchase_order,
    purchase_order_status,
    purchase_order_warnings,
)
from document_extractor.domain.purchase_order.models import (
    PurchaseOrderData,
    PurchaseOrderExtractionResult,
    PurchaseOrderLine,
    PurchaseOrderParty,
)

_LABELS = {
    "order_number": "Purchase order number",
    "issue_date": "Issue date",
    "expected_delivery_date": "Expected delivery date",
    "buyer_name": "Buyer",
    "buyer_tax_id": "Buyer tax ID",
    "supplier_name": "Supplier",
    "supplier_tax_id": "Supplier tax ID",
    "shipping_address": "Shipping address",
    "payment_terms": "Payment terms",
    "subtotal": "Subtotal",
    "tax_amount": "Tax amount",
    "total_amount": "Total",
    "currency": "Currency",
}
_DATE = (
    r"(?:\d{4}\s*-\s*\d{1,2}\s*-\s*\d{1,2}|"
    r"\d{1,2}\s*[./-]\s*\d{1,2}\s*[./-]\s*\d{2,4})"
)
_MONEY = r"[-+]?\s*\d(?:[\d.,'\u2019 ]*\d)?"
_COLUMN_NUMBER = r"[-+]?\d[\d.,]*"
_CURRENCY = r"(?:EUR|USD|GBP|\u20ac|\$|\u00a3)"
_VALUE_END = r"(?=$|[ \t\n.;,)])"


class RuleBasedPurchaseOrderParser:
    """Parse common Spanish and English purchase-order labels."""

    # Each field maps ordered regex alternatives to its base confidence.
    _patterns: dict[str, tuple[tuple[str, ...], float]] = {
        "order_number": (
            (
                r"\b(?:pedido\s+de\s+compra|orden\s+de\s+compra|"
                r"purchase\s+order|purchase\s+order\s+number|po)\s*"
                r"(?:n(?:úm(?:ero)?)?\.?|n[º°o]\.?|no\.?|number|#)?"
                r"\s*[:\-]?\s*"
                r"(?P<value>(?=[A-Z0-9./_-]*\d)"
                r"[A-Z0-9][A-Z0-9./_-]{1,39})\b",
            ),
            0.94,
        ),
        "issue_date": (
            (
                rf"\b(?:fecha\s+(?:del\s+)?pedido|"
                rf"fecha\s+de\s+emisión|issue\s+date|order\s+date)"
                rf"\s*[:\-]?\s*(?P<value>{_DATE})\b",
            ),
            0.9,
        ),
        "expected_delivery_date": (
            (
                rf"\b(?:fecha\s+(?:prevista\s+)?de\s+entrega|"
                rf"entrega\s+prevista|"
                rf"expected\s+delivery(?:\s+date)?|delivery\s+date)"
                rf"\s*[:\-]?\s*(?P<value>{_DATE})\b",
            ),
            0.9,
        ),
        "buyer_name": (
            (
                r"^(?:comprador|cliente|buyer|bill\s+to)"
                r"\s*[:\-]\s*(?P<value>[^\n]{2,120})$",
            ),
            0.84,
        ),
        "buyer_tax_id": (
            (
                r"^(?:nif|cif|vat|tax\s+id)\s+"
                r"(?:comprador|cliente|buyer)\s*[:\-]\s*"
                r"(?P<value>[A-Z0-9 -]{6,24})$",
            ),
            0.88,
        ),
        "supplier_name": (
            (
                r"^(?:proveedor|vendedor|supplier|vendor)"
                r"\s*[:\-]\s*(?P<value>[^\n]{2,120})$",
            ),
            0.84,
        ),
        "supplier_tax_id": (
            (
                r"^(?:nif|cif|vat|tax\s+id)\s+"
                r"(?:proveedor|vendedor|supplier|vendor)\s*[:\-]\s*"
                r"(?P<value>[A-Z0-9 -]{6,24})$",
            ),
            0.88,
        ),
        "shipping_address": (
            (
                r"^(?:dirección\s+de\s+entrega|enviar\s+a|"
                r"shipping\s+address|ship\s+to)"
                r"\s*[:\-]\s*(?P<value>[^\n]{4,180})$",
            ),
            0.82,
        ),
        "payment_terms": (
            (
                r"^(?:condiciones\s+de\s+pago|forma\s+de\s+pago|"
                r"payment\s+terms)"
                r"\s*[:\-]\s*(?P<value>[^\n]{2,100})$",
            ),
            0.84,
        ),
        "subtotal": (
            (
                rf"\b(?:subtotal|importe\s+neto|net\s+amount)"
                rf"\s*[:\-]?\s*(?:{_CURRENCY}\s*)?"
                rf"(?P<value>{_MONEY})(?:\s*{_CURRENCY})?{_VALUE_END}",
            ),
            0.9,
        ),
        "tax_amount": (
            (
                rf"\b(?:cuota\s+(?:de\s+)?iva|"
                rf"importe\s+(?:de\s+)?iva|iva|vat)"
                rf"(?:\s*\(?\d{{1,2}}(?:[.,]\d+)?\s*%\)?)?"
                rf"\s*[:\-]?\s*(?:{_CURRENCY}\s*)?"
                rf"(?P<value>{_MONEY})(?:\s*{_CURRENCY})?{_VALUE_END}",
            ),
            0.86,
        ),
        "total_amount": (
            (
                rf"\b(?:total\s+pedido|importe\s+total|"
                rf"grand\s+total|order\s+total|total)"
                rf"\s*[:\-]?\s*(?:{_CURRENCY}\s*)?"
                rf"(?P<value>{_MONEY})(?:\s*{_CURRENCY})?{_VALUE_END}",
            ),
            0.95,
        ),
    }

    # Product rows require explicit SKU, description and amount columns.
    _line_pattern = re.compile(
        rf"^(?P<sku>[A-Z0-9][A-Z0-9._/-]{{1,24}})\s+"
        rf"(?P<description>.+?\S)\s+"
        rf"(?P<quantity>\d+(?:[.,]\d+)?)\s+"
        rf"(?P<unit_price>{_COLUMN_NUMBER})\s*(?:{_CURRENCY})?\s+"
        rf"(?P<line_total>{_COLUMN_NUMBER})\s*(?:{_CURRENCY})?$",
        re.IGNORECASE,
    )

    def parse(
        self,
        text: str,
        acquisition_method: ContentAcquisitionMethod = (
            ContentAcquisitionMethod.EMBEDDED_TEXT
        ),
    ) -> PurchaseOrderExtractionResult:
        """Extract normalized purchase-order data and review warnings.

        Args:
            text: Readable purchase-order text.
            acquisition_method: Method used to obtain the text.

        Returns:
            The locally extracted purchase-order result.
        """
        normalized = self._normalize(text)
        fields = {
            name: ExtractedField(label=label)
            for name, label in _LABELS.items()
        }
        for name, (patterns, confidence) in self._patterns.items():
            match = self._first_match(patterns, normalized)
            if match is None:
                continue
            value = self._convert(name, match.group("value"))
            if value is not None:
                fields[name] = ExtractedField(
                    label=_LABELS[name],
                    value=value,
                    confidence=confidence,
                    extraction_method=DataExtractionMethod.RULE_BASED,
                )
        self._assign_currency(normalized, fields)
        lines = tuple(self._parse_lines(normalized))
        data = PurchaseOrderData(
            order_number=fields["order_number"],
            issue_date=fields["issue_date"],
            expected_delivery_date=fields["expected_delivery_date"],
            buyer=PurchaseOrderParty(
                fields["buyer_name"], fields["buyer_tax_id"]
            ),
            supplier=PurchaseOrderParty(
                fields["supplier_name"], fields["supplier_tax_id"]
            ),
            shipping_address=fields["shipping_address"],
            payment_terms=fields["payment_terms"],
            subtotal=fields["subtotal"],
            tax_amount=fields["tax_amount"],
            total_amount=fields["total_amount"],
            currency=fields["currency"],
            line_items=lines,
        )
        assessment = assess_purchase_order(data)
        return PurchaseOrderExtractionResult(
            status=purchase_order_status(data, assessment),
            data=data,
            acquisition_method=acquisition_method,
            extraction_method=DataExtractionMethod.RULE_BASED,
            warnings=purchase_order_warnings(data, assessment),
        )

    @staticmethod
    def _first_match(
        patterns: tuple[str, ...],
        text: str,
    ) -> re.Match[str] | None:
        """Return the first matching regex alternative.

        Args:
            patterns: Ordered regex alternatives.
            text: Normalized text to search.

        Returns:
            The first match, or ``None`` when no alternative matches.
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
    def _convert(cls, name: str, value: str) -> FieldScalar | None:
        """Convert a regex value to its domain representation.

        Args:
            name: Target purchase-order field name.
            value: Raw matched value.

        Returns:
            A typed field value, or ``None`` when parsing fails.
        """
        match name:
            case "subtotal" | "tax_amount" | "total_amount":
                return cls._decimal(value)
            case "issue_date" | "expected_delivery_date":
                return cls._date(value)
            case _:
                return value.strip(" :-|") or None

    @classmethod
    def _parse_lines(cls, text: str) -> list[PurchaseOrderLine]:
        """Extract structured product rows from normalized text.

        Args:
            text: Normalized purchase-order text.

        Returns:
            Recognized purchase-order lines in document order.
        """
        result = []
        for raw_line in text.splitlines():
            match = cls._line_pattern.match(raw_line.strip())
            if match is None:
                continue
            quantity = cls._decimal(match.group("quantity"))
            unit_price = cls._decimal(match.group("unit_price"))
            total = cls._decimal(match.group("line_total"))
            if quantity is None or unit_price is None or total is None:
                continue
            # Keep inconsistent rows for review at lower confidence.
            confidence = (
                0.86
                if abs(quantity * unit_price - total) <= Decimal("0.02")
                else 0.58
            )
            result.append(
                PurchaseOrderLine(
                    sku=match.group("sku"),
                    description=match.group("description").strip(),
                    quantity=quantity,
                    unit_price=unit_price,
                    line_total=total,
                    confidence=confidence,
                    extraction_method=DataExtractionMethod.RULE_BASED,
                )
            )
        return result

    @staticmethod
    def _assign_currency(text: str, fields: dict[str, ExtractedField]) -> None:
        """Assign the first supported currency found in the document.

        Args:
            text: Normalized purchase-order text.
            fields: Mutable extracted-field mapping.
        """
        for pattern, code in (
            (r"(?:€|\bEUR\b)", "EUR"),
            (r"(?:\$|\bUSD\b)", "USD"),
            (r"(?:£|\bGBP\b)", "GBP"),
        ):
            if re.search(pattern, text, re.IGNORECASE):
                fields["currency"] = ExtractedField(
                    label=_LABELS["currency"],
                    value=code,
                    confidence=0.92,
                    extraction_method=DataExtractionMethod.RULE_BASED,
                )
                return

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize horizontal whitespace while preserving lines.

        Args:
            text: Raw readable document text.

        Returns:
            Normalized non-empty lines.
        """
        lines = (
            re.sub(r"[ \t\u00a0]+", " ", line).strip()
            for line in text.replace("\r", "\n").split("\n")
        )
        return "\n".join(line for line in lines if line)

    @staticmethod
    def _decimal(value: str) -> Decimal | None:
        """Parse common decimal and thousands-separator conventions.

        Args:
            value: Raw monetary or quantity value.

        Returns:
            Parsed decimal, or ``None`` when the value is invalid.
        """
        compact = re.sub(
            r"(?:EUR|USD|GBP|€|\$|£|\s|'|’|\u00a0)",
            "",
            value,
            flags=re.IGNORECASE,
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
            compact = compact.replace(
                "." if decimal_separator == "," else ",", ""
            ).replace(decimal_separator, ".")
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
        """Parse supported Spanish and ISO date formats.

        Args:
            value: Raw date value.

        Returns:
            Parsed date, or ``None`` when no format matches.
        """
        compact = re.sub(r"\s+", "", value)
        for pattern in (
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d.%m.%Y",
            "%Y-%m-%d",
            "%d/%m/%y",
            "%d-%m-%y",
        ):
            try:
                return datetime.strptime(compact, pattern).date()
            except ValueError:
                continue
        return None
