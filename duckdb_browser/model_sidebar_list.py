from typing import List, Optional, Union, cast, overload
from PySide6.QtCore import (
    QPersistentModelIndex,
    Qt,
    QModelIndex,
    QAbstractItemModel,
    QObject,
)
from typing import Any, Tuple
from duckdb import DuckDBPyConnection


class DatabaseItem:
    def __init__(
        self, name: str, item_type: str, parent: Optional["DatabaseItem"] = None
    ):
        self.name = name
        self.type = item_type
        self.parent = parent
        self.children: List["DatabaseItem"] = []

    def add_child(self, child: "DatabaseItem") -> None:
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
        self._fetch_structure()

    def _fetch_structure(self) -> None:
        # Fetch schemas
        schemas_query = "SELECT DISTINCT schema_name FROM information_schema.schemata ORDER BY schema_name"
        for (schema_name,) in self.connection.execute(schemas_query).fetchall():
            schema_item = DatabaseItem(schema_name, "schema", self.root)
            self.root.add_child(schema_item)

            tables_item = DatabaseItem("Tables", "category", schema_item)
            views_item = DatabaseItem("Views", "category", schema_item)
            schema_item.add_child(tables_item)
            schema_item.add_child(views_item)

            # Fetch tables and views for each schema
            objects_query = f"""
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = '{schema_name}'
            ORDER BY table_type, table_name
            """
            for table_name, table_type in self.connection.execute(objects_query).fetchall():
                parent_item = tables_item if table_type == 'BASE TABLE' else views_item
                item = DatabaseItem(table_name, table_type.lower(), parent_item)
                parent_item.add_child(item)

                # Fetch columns for each table/view
                columns_query = f"DESCRIBE {schema_name}.{table_name}"
                try:
                    for column_info in self.connection.execute(columns_query).fetchall():
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

    def get_item_info(
        self, index: Union[QModelIndex, QPersistentModelIndex]
    ) -> Tuple[str, str, Optional[str], Optional[str]]:
        item = index.internalPointer()
        if item.type == "column":
            table_item = item.parent
            schema_item = table_item.parent.parent
            return item.type, schema_item.name, table_item.name, item.name.split()[0]
        elif item.type in ("table", "view"):
            schema_item = item.parent.parent
            return item.type, schema_item.name, item.name, None
        return item.type, item.name, None, None
