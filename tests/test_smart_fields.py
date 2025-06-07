"""Test smart field selection functionality."""

from unittest.mock import Mock

import pytest

from mcp_server_odoo.tools import OdooToolHandler


class TestSmartFieldSelection:
    """Test smart field selection logic."""

    @pytest.fixture
    def tool_handler(self):
        """Create a tool handler with mocked dependencies."""
        app = Mock()
        connection = Mock()
        access_controller = Mock()
        config = Mock()
        config.default_limit = 10
        config.max_limit = 100

        return OdooToolHandler(app, connection, access_controller, config)

    def test_should_include_field_always_include(self, tool_handler):
        """Test that essential fields are always included."""
        # Essential fields should always be included
        assert tool_handler._should_include_field_by_default("id", {}) is True
        assert tool_handler._should_include_field_by_default("name", {}) is True
        assert tool_handler._should_include_field_by_default("display_name", {}) is True
        assert tool_handler._should_include_field_by_default("active", {}) is True

    def test_should_include_field_exclude_technical(self, tool_handler):
        """Test that technical fields are excluded."""
        # Fields with technical prefixes should be excluded
        assert tool_handler._should_include_field_by_default("_order", {}) is False
        assert tool_handler._should_include_field_by_default("message_follower_ids", {}) is False
        assert tool_handler._should_include_field_by_default("activity_ids", {}) is False
        assert tool_handler._should_include_field_by_default("website_message_ids", {}) is False

        # Specific technical fields should be excluded
        assert tool_handler._should_include_field_by_default("write_date", {}) is False
        assert tool_handler._should_include_field_by_default("create_date", {}) is False
        assert tool_handler._should_include_field_by_default("__last_update", {}) is False

    def test_should_include_field_exclude_binary(self, tool_handler):
        """Test that binary and large fields are excluded."""
        assert tool_handler._should_include_field_by_default("image", {"type": "binary"}) is False
        assert tool_handler._should_include_field_by_default("photo", {"type": "image"}) is False
        assert (
            tool_handler._should_include_field_by_default("description_html", {"type": "html"})
            is False
        )

    def test_should_include_field_exclude_computed_nonstored(self, tool_handler):
        """Test that expensive computed fields are excluded."""
        # Computed non-stored field should be excluded
        field_info = {"type": "char", "compute": "some_method", "store": False}
        assert tool_handler._should_include_field_by_default("computed_field", field_info) is False

        # Computed stored field should be included
        field_info = {"type": "char", "compute": "some_method", "store": True, "searchable": True}
        assert tool_handler._should_include_field_by_default("computed_field", field_info) is True

    def test_should_include_field_exclude_relations(self, tool_handler):
        """Test that one2many and many2many fields are excluded."""
        assert (
            tool_handler._should_include_field_by_default("child_ids", {"type": "one2many"})
            is False
        )
        assert (
            tool_handler._should_include_field_by_default("tag_ids", {"type": "many2many"}) is False
        )

        # Many2one should be included
        assert (
            tool_handler._should_include_field_by_default(
                "partner_id", {"type": "many2one", "store": True, "searchable": True}
            )
            is True
        )

    def test_should_include_field_required(self, tool_handler):
        """Test that required fields are included."""
        field_info = {"type": "char", "required": True}
        assert tool_handler._should_include_field_by_default("required_field", field_info) is True

    def test_should_include_field_simple_stored(self, tool_handler):
        """Test that simple stored searchable fields are included."""
        simple_types = [
            "char",
            "text",
            "boolean",
            "integer",
            "float",
            "date",
            "datetime",
            "selection",
            "many2one",
        ]

        for field_type in simple_types:
            field_info = {"type": field_type, "store": True, "searchable": True}
            assert (
                tool_handler._should_include_field_by_default(f"test_{field_type}", field_info)
                is True
            )

        # Non-searchable stored field should not be included
        field_info = {"type": "char", "store": True, "searchable": False}
        assert tool_handler._should_include_field_by_default("non_searchable", field_info) is False

    def test_get_smart_default_fields_success(self, tool_handler):
        """Test successful smart field selection."""
        # Mock fields_get response
        mock_fields = {
            "id": {"type": "integer"},
            "name": {"type": "char", "required": True},
            "display_name": {"type": "char"},
            "email": {"type": "char", "store": True, "searchable": True},
            "phone": {"type": "char", "store": True, "searchable": True},
            "is_company": {"type": "boolean", "store": True, "searchable": True},
            # Fields that should be excluded
            "message_ids": {"type": "one2many"},
            "_order": {"type": "char"},
            "image_1920": {"type": "binary"},
            "write_date": {"type": "datetime"},
            "access_token": {"type": "char"},
        }

        tool_handler.connection.fields_get.return_value = mock_fields

        result = tool_handler._get_smart_default_fields("res.partner")

        # Should include smart selection
        assert "id" in result
        assert "name" in result
        assert "display_name" in result
        assert "email" in result
        assert "phone" in result
        assert "is_company" in result

        # Should exclude technical/binary/relation fields
        assert "message_ids" not in result
        assert "_order" not in result
        assert "image_1920" not in result
        assert "write_date" not in result
        assert "access_token" not in result

    def test_get_smart_default_fields_error_handling(self, tool_handler):
        """Test error handling in smart field selection."""
        # Mock fields_get to raise an exception
        tool_handler.connection.fields_get.side_effect = Exception("Connection error")

        # Should return None to indicate fallback to all fields
        result = tool_handler._get_smart_default_fields("res.partner")
        assert result is None

    def test_get_smart_default_fields_empty_result(self, tool_handler):
        """Test handling of models with no suitable fields."""
        # Mock fields_get with all excluded fields
        mock_fields = {
            "_order": {"type": "char"},
            "message_ids": {"type": "one2many"},
            "activity_ids": {"type": "one2many"},
        }

        tool_handler.connection.fields_get.return_value = mock_fields

        result = tool_handler._get_smart_default_fields("weird.model")

        # Should return minimal default fields
        assert result == ["id", "name", "display_name"]

    @pytest.mark.asyncio
    async def test_get_record_with_smart_defaults(self, tool_handler):
        """Test get_record using smart defaults."""
        # Setup mocks
        tool_handler.connection.is_authenticated = True
        tool_handler.connection.fields_get.return_value = {
            "id": {"type": "integer"},
            "name": {"type": "char", "required": True},
            "email": {"type": "char", "store": True, "searchable": True},
            "message_ids": {"type": "one2many"},
            "image_1920": {"type": "binary"},
        }

        tool_handler.connection.read.return_value = [
            {"id": 1, "name": "Test Partner", "email": "test@example.com"}
        ]

        # Call without fields parameter
        result = await tool_handler._handle_get_record_tool("res.partner", 1, None)

        # Should have the record data
        assert result["id"] == 1
        assert result["name"] == "Test Partner"
        assert result["email"] == "test@example.com"

        # Should have metadata
        assert "_metadata" in result
        assert result["_metadata"]["field_selection_method"] == "smart_defaults"
        assert result["_metadata"]["fields_returned"] == 3  # id, name, email
        assert result["_metadata"]["total_fields_available"] == 5
        assert "Limited fields returned" in result["_metadata"]["note"]

        # Should have called read with smart fields
        tool_handler.connection.read.assert_called_once()
        call_args = tool_handler.connection.read.call_args
        assert call_args[0][0] == "res.partner"  # model
        assert call_args[0][1] == [1]  # record_id
        assert set(call_args[0][2]) == {"id", "name", "email"}  # smart fields

    @pytest.mark.asyncio
    async def test_get_record_with_all_fields(self, tool_handler):
        """Test get_record with __all__ parameter."""
        # Setup mocks
        tool_handler.connection.is_authenticated = True
        tool_handler.connection.read.return_value = [
            {
                "id": 1,
                "name": "Test Partner",
                "email": "test@example.com",
                "phone": "123456",
                "message_ids": [1, 2, 3],
                "image_1920": "base64data...",
                # ... many more fields
            }
        ]

        # Call with __all__
        result = await tool_handler._handle_get_record_tool("res.partner", 1, ["__all__"])

        # Should not have metadata
        assert "_metadata" not in result

        # Should have called read with None (all fields)
        tool_handler.connection.read.assert_called_once_with("res.partner", [1], None)

    @pytest.mark.asyncio
    async def test_get_record_with_specific_fields(self, tool_handler):
        """Test get_record with specific fields."""
        # Setup mocks
        tool_handler.connection.is_authenticated = True
        tool_handler.connection.read.return_value = [
            {"id": 1, "name": "Test Partner", "phone": "123456"}
        ]

        # Call with specific fields
        fields = ["name", "phone"]
        result = await tool_handler._handle_get_record_tool("res.partner", 1, fields)

        # Should not have metadata
        assert "_metadata" not in result

        # Should have called read with specific fields
        tool_handler.connection.read.assert_called_once_with("res.partner", [1], fields)

    def test_field_sorting(self, tool_handler):
        """Test that fields are sorted correctly."""
        # Mock fields_get response
        mock_fields = {
            "zip": {"type": "char", "store": True, "searchable": True},
            "email": {"type": "char", "store": True, "searchable": True},
            "active": {"type": "boolean"},
            "name": {"type": "char", "required": True},
            "display_name": {"type": "char"},
            "id": {"type": "integer"},
            "city": {"type": "char", "store": True, "searchable": True},
        }

        tool_handler.connection.fields_get.return_value = mock_fields

        result = tool_handler._get_smart_default_fields("res.partner")

        # Priority fields should come first in order
        assert result[0] == "id"
        assert result[1] == "name"
        assert result[2] == "display_name"
        assert result[3] == "active"

        # Other fields should be alphabetical
        other_fields = result[4:]
        assert other_fields == sorted(other_fields)
