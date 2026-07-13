from __future__ import annotations

from qfluentwidgets import MessageBox


class IndexRefreshDialog(MessageBox):
    def __init__(self, parent=None):
        super().__init__("刷新索引", "该操作会重新检查题库文件夹，题库数量的多少会影响等待时间的长短", parent)
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
