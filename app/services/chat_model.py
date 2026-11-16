from __future__ import annotations

import time

from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, Qt, Slot


class ChatModel(QAbstractListModel):
    RoleRole = Qt.UserRole + 1
    TextRole = Qt.UserRole + 2
    TimeRole = Qt.UserRole + 3
    DoneRole = Qt.UserRole + 4

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: list[dict] = []

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802, B008
        return 0 if parent.isValid() else len(self._items)

    def roleNames(self) -> dict[int, QByteArray]:  # noqa: N802
        return {self.RoleRole: QByteArray(b"role"), self.TextRole: QByteArray(b"text"),
                self.TimeRole: QByteArray(b"time"), self.DoneRole: QByteArray(b"done")}

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        item = self._items[index.row()]
        return {self.RoleRole: item["role"], self.TextRole: item["text"], self.TimeRole: item["time"],
                self.DoneRole: item["done"], Qt.DisplayRole: item["text"]}.get(role)

    def append(self, role: str, text: str, done: bool = True, ts: float | None = None) -> int:
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append({"role": role, "text": text, "done": done,
                            "time": time.strftime("%H:%M", time.localtime(ts or time.time()))})
        self.endInsertRows()
        return row

    def update(self, row: int, text: str, done: bool = False) -> None:
        if 0 <= row < len(self._items):
            self._items[row]["text"] = text
            self._items[row]["done"] = done
            idx = self.index(row)
            self.dataChanged.emit(idx, idx, [self.TextRole, self.DoneRole])

    @Slot()
    def clear(self) -> None:
        self.beginResetModel()
        self._items.clear()
        self.endResetModel()

    def count(self) -> int:
        return len(self._items)
