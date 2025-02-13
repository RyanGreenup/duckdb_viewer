from typing import List, Optional, Union, cast, overload, Tuple, Any, Dict
from PySide6.QtCore import (
    QPersistentModelIndex,
    Qt,
    QModelIndex,
    QAbstractItemModel,
    QObject,
)
from duckdb import DuckDBPyConnection


class DatabaseItem:
    def __init__(
        self, name: str, item_type: str, parent: Optional["DatabaseItem"] = None
    ):
        self.name = name
        self.type = item_type
        self.parent = parent
        self.children: List["DatabaseItem"] = []
        if parent is not None:
            parent.children.append(self)

    def add_child(self, child: "DatabaseItem") -> None:
        child.parent = self
        if child not in self.children:
            self.children.append(child)

    def child_count(self) -> int:
        return len(self.children)

    def row(self) -> int:
        if self.parent:
            return self.parent.children.index(self)
        return 0


class TableListModel(QAbstractItemModel):
    def __init__(self, connection: DuckDBPyConnection):
        super().__init__()
        self.connection = connection
        self.root = DatabaseItem("Database", "root")
        self.filter_string: str | None = None
        self._fetch_structure(None)

    def update_filter(self, filter_string: str | None) -> None:
        """Update the model with a new filter while maintaining model consistency."""
        self.layoutAboutToBeChanged.emit()
        self.root = DatabaseItem("Database", "root")
        self.filter_string = filter_string
        self._fetch_structure(filter_string)
        self.layoutChanged.emit()

    def _fetch_structure(self, filter_string: str | None) -> None:
        # Fetch schemas
        schemas_query = "SELECT DISTINCT schema_name FROM information_schema.schemata ORDER BY schema_name"
        for (schema_name,) in self.connection.execute(schemas_query).fetchall():
            schema_item = DatabaseItem(schema_name, "schema", self.root)
            tables_item = DatabaseItem("Tables", "category", schema_item)
            views_item = DatabaseItem("Views", "category", schema_item)

            # Fetch tables and views for each schema
            objects_query = f"""
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = '{schema_name}'
            ORDER BY table_type, table_name
            """
            if filter_string is not None:
                objects_query = f"""
                SELECT table_name, table_type
                FROM information_schema.tables
                WHERE table_schema = '{schema_name}'
                    AND table_name LIKE '%{filter_string}%'
                ORDER BY table_type, table_name
                """
            for table_name, table_type in self.connection.execute(
                objects_query
            ).fetchall():
                parent_item = tables_item if table_type == "BASE TABLE" else views_item
                item = DatabaseItem(table_name, table_type.lower(), parent_item)
                parent_item.add_child(item)

                # Fetch columns for each table/view
                columns_query = f"DESCRIBE {schema_name}.{table_name}"
                try:
                    for column_info in self.connection.execute(
                        columns_query
                    ).fetchall():
                        column_name = column_info[0]
                        column_type = column_info[1]
                        column_item = DatabaseItem(
                            f"{column_name} ({column_type})", "column", item
                        )
                        item.add_child(column_item)
                except Exception as e:
                    print(f"Error fetching columns for {schema_name}.{table_name}: {e}")

    def rowCount(
        self, parent: Union[QModelIndex, QPersistentModelIndex] = QModelIndex()
    ) -> int:
        if parent.isValid():
            item: DatabaseItem = parent.internalPointer()
            return item.child_count()
        return self.root.child_count()

    def columnCount(
        self, parent: Union[QModelIndex, QPersistentModelIndex] = QModelIndex()
    ) -> int:
        return 1

    def data(
        self,
        index: Union[QModelIndex, QPersistentModelIndex],
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid():
            return None

        item = index.internalPointer()

        if role == Qt.ItemDataRole.DisplayRole:
            return item.name
        elif role == Qt.ItemDataRole.UserRole:
            return item.type

        return None

    def index(
        self,
        row: int,
        column: int,
        parent: Union[QModelIndex, QPersistentModelIndex] = QModelIndex(),
    ) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parent_item = self.root
        else:
            parent_item = cast(DatabaseItem, parent.internalPointer())

        child_item = parent_item.children[row]
        if child_item:
            return self.createIndex(row, column, child_item)
        return QModelIndex()

    @overload
    def parent(self) -> QObject: ...

    @overload
    def parent(
        self, child: Union[QModelIndex, QPersistentModelIndex]
    ) -> QModelIndex: ...

    def parent(
        self, child: Union[QModelIndex, QPersistentModelIndex, None] = None
    ) -> Union[QObject, QModelIndex]:
        if child is None:
            return super().parent()

        if not child.isValid():
            return QModelIndex()

        child_item: DatabaseItem = child.internalPointer()
        parent_item = child_item.parent

        if parent_item is None or parent_item == self.root:
            return QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def export_fold_state(self) -> Dict[str, bool]:
        """Export the fold state of the tree based on item ancestry."""
        fold_state: Dict[str, bool] = {}
        
        def process_item(item: DatabaseItem, ancestry: List[str] = []) -> None:
            current_path = '/'.join(ancestry + [item.name])
            if item.child_count() > 0:
                # Get the QModelIndex for this item to check its expansion state
                parent_index = self.createIndex(item.row(), 0, item)
                # The view must be accessible to check expansion state
                if hasattr(self, 'tree_view'):
                    fold_state[current_path] = self.tree_view.isExpanded(parent_index)
                
                # Process children
                for child in item.children:
                    process_item(child, ancestry + [item.name])
        
        # Start from root's children (schemas)
        for schema_item in self.root.children:
            process_item(schema_item)
            
        return fold_state

    @staticmethod
    def restore_fold_state(tree_view: Any, fold_state: Dict[str, bool]) -> None:
        """Restore the fold state of the tree based on the saved state."""
        def process_item(index: QModelIndex, current_path: List[str] = []) -> None:
            model = tree_view.model()
            item: DatabaseItem = index.internalPointer()
            
            full_path = '/'.join(current_path + [item.name])
            if full_path in fold_state:
                tree_view.setExpanded(index, fold_state[full_path])
            
            # Process children
            for row in range(model.rowCount(index)):
                child_index = model.index(row, 0, index)
                process_item(child_index, current_path + [item.name])
        
        # Start from root level
        model = tree_view.model()
        for row in range(model.rowCount(QModelIndex())):
            index = model.index(row, 0, QModelIndex())
            process_item(index)

    def get_item_info(
        self, index: Union[QModelIndex, QPersistentModelIndex]
    ) -> Tuple[str, str, Optional[str], Optional[str]]:
        item: DatabaseItem = index.internalPointer()
        if item.type == "column":
            table_item = item.parent
            schema_item = table_item.parent.parent if table_item and table_item.parent else None
            return (
                item.type,
                schema_item.name if schema_item else "",
                table_item.name if table_item else "",
                item.name.split()[0],
            )
        elif item.type in ("table", "view", "base table"):
            schema_item = item.parent.parent if item.parent else None
            return (
                item.type,
                schema_item.name if schema_item else "",
                item.name,
                None,
            )
        return item.type, item.name, None, None
