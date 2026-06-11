"""
Workflow Mixin - composite SAP GUI operations.

These helpers combine common low-level controller operations into one COM
round trip.  They are intentionally generic and avoid transaction-specific
business logic.
"""

from typing import Any, Dict


class WorkflowMixin:
    """Mixin for high-level workflow operations built from existing tools."""

    def _screen_fingerprint(self, screen: Dict[str, Any]) -> str:
        keys = ("active_window", "transaction", "program", "screen_number", "title")
        return "|".join(str(screen.get(key, "") or "") for key in keys)

    def get_light_snapshot(self) -> Dict[str, Any]:
        """Return a lightweight screen snapshot without enumerating elements."""
        self._require_session()

        screen = self.get_screen_info()
        result: Dict[str, Any] = {
            "screen": screen,
            "active_window": screen.get("active_window", "wnd[0]"),
            "fingerprint": self._screen_fingerprint(screen),
        }

        if result["active_window"] != "wnd[0]":
            result["popup"] = self.get_popup_window()

        return result

    def set_fields_and_enter(
        self,
        fields: Dict[str, str],
        *,
        skip_readonly: bool = True,
    ) -> Dict[str, Any]:
        """Set multiple fields, press Enter once, and return validation screen."""
        self._require_session()

        result = self.set_batch_fields(
            fields,
            skip_readonly=skip_readonly,
            validate=True,
        )
        result["action"] = "set_fields_and_enter"

        validation = result.get("validation")
        if isinstance(validation, dict) and isinstance(validation.get("screen"), dict):
            result["screen"] = validation["screen"]
        else:
            result["screen"] = self.get_screen_info()

        return result

    def select_popup_table_row_and_confirm(
        self,
        table_id: str,
        row: int,
        *,
        confirm_action: str = "confirm",
    ) -> Dict[str, Any]:
        """Select a row in a popup table and confirm the popup in one call."""
        self._require_session()

        if confirm_action not in {"confirm", "auto"}:
            raise ValueError("confirm_action must be 'confirm' or 'auto'")

        popup_before = self.get_popup_window()
        selection = self.select_table_row(table_id, row)
        if isinstance(selection, dict) and selection.get("error"):
            return {
                "action": "select_popup_table_row_and_confirm",
                "table_id": table_id,
                "selected_row": row,
                "selection": selection,
                "status": "selection_failed",
                "error": selection["error"],
                "popup_before": popup_before,
            }

        confirmation = self.handle_popup(confirm_action)
        result: Dict[str, Any] = {
            "action": "select_popup_table_row_and_confirm",
            "table_id": table_id,
            "selected_row": row,
            "selection": selection,
            "confirmation": confirmation,
            "popup_before": popup_before,
            "popup_closed": confirmation.get("popup_closed", False),
        }

        if isinstance(confirmation, dict) and confirmation.get("error"):
            result["status"] = "confirm_failed"
            result["error"] = confirmation["error"]
        else:
            result["status"] = "success"

        if isinstance(confirmation, dict) and isinstance(confirmation.get("screen"), dict):
            result["screen"] = confirmation["screen"]
        else:
            result["screen"] = self.get_screen_info()

        return result
