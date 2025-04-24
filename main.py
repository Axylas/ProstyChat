import sys
import os
import json
import markdown
import uuid
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTextEdit, QPushButton,
    QScrollArea, QFrame, QSizePolicy, QHBoxLayout, QFileDialog, QLabel,
    QListWidget, QListWidgetItem, QSplitter
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from openai import OpenAI

client = OpenAI(api_key="TWOJE API")

class Worker(QThread):
    result_ready = pyqtSignal(str)

    def __init__(self, messages):
        super().__init__()
        self.messages = messages

    def run(self):
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "system", "content": "Jesteś pomocnym asystentem."}] + self.messages
            )
            reply = response.choices[0].message.content
        except Exception as e:
            reply = f"Błąd: {e}"
        self.result_ready.emit(reply)

class ChatWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nowoczesny ChatGPT - PyQt5")
        self.setGeometry(200, 100, 1000, 700)
        self.set_dark_palette()
        self.chat_id = str(uuid.uuid4())
        self.messages = []

        os.makedirs("chats", exist_ok=True)
        self.init_ui()
        self.create_new_chat()

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        self.chat_list = QListWidget()
        self.chat_list.setFixedWidth(200)
        self.chat_list.itemClicked.connect(self.load_selected_chat)
        main_layout.addWidget(self.chat_list)

        right_panel = QVBoxLayout()

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.chat_area = QWidget()
        self.chat_area.setStyleSheet("background-color: #1e1e1e;")
        self.chat_layout = QVBoxLayout(self.chat_area)
        self.chat_layout.addStretch(1)
        self.scroll.setWidget(self.chat_area)
        right_panel.addWidget(self.scroll)

        self.input = QTextEdit()
        self.input.setFixedHeight(80)
        self.input.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d30;
                color: #ffffff;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        right_panel.addWidget(self.input)

        button_layout = QHBoxLayout()
        self.send_button = QPushButton("Wyślij")
        self.send_button.clicked.connect(self.handle_send_click)
        self.send_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #0078D4, stop:1 #005A9E);
                color: white;
                padding: 10px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
        """)
        self.new_chat_button = QPushButton("+ Nowy czat")
        self.new_chat_button.clicked.connect(self.create_new_chat)
        button_layout.addWidget(self.new_chat_button)
        button_layout.addStretch()
        button_layout.addWidget(self.send_button)
        right_panel.addLayout(button_layout)

        main_layout.addLayout(right_panel)
        self.load_chat_list()

    def set_dark_palette(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(45, 45, 48))
        palette.setColor(QPalette.Base, QColor(30, 30, 30))
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(45, 45, 48))
        palette.setColor(QPalette.ButtonText, Qt.white)
        self.setPalette(palette)

    def add_message(self, text, is_user=True):
        html = markdown.markdown(text)
        view = QWebEngineView()
        bg_color = "#0078D4" if is_user else "#444"
        text_color = "white"
        view.setHtml(f"""
            <html><body style="background-color: {bg_color}; 
                               color: {text_color}; 
                               font-family: sans-serif; 
                               padding: 10px; border-radius: 10px;">
                {html}
            </body></html>
        """)
        view.setMinimumHeight(100)
        view.setMaximumHeight(300)
        view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        frame = QFrame()
        frame_layout = QVBoxLayout()
        frame_layout.addWidget(view)
        frame_layout.setAlignment(Qt.AlignRight if is_user else Qt.AlignLeft)
        frame.setLayout(frame_layout)

        self.chat_layout.insertWidget(self.chat_layout.count() - 1, frame)
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())

    def handle_send_click(self):
        user_input = self.input.toPlainText().strip()
        if not user_input:
            return

        self.add_message(user_input, is_user=True)
        self.messages.append({"role": "user", "content": user_input})
        self.input.clear()
        QApplication.processEvents()

        self.wait_label = QLabel("Asystent pisze wiadomość...")
        self.wait_label.setStyleSheet("color: #888; margin-left: 12px;")
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, self.wait_label)

        self.worker = Worker(self.messages.copy())
        self.worker.result_ready.connect(self.display_response)
        self.worker.start()

    def display_response(self, reply):
        if hasattr(self, 'wait_label'):
            self.chat_layout.removeWidget(self.wait_label)
            self.wait_label.deleteLater()
            del self.wait_label
        self.messages.append({"role": "assistant", "content": reply})
        self.save_history()
        self.add_message(reply, is_user=False)

    def save_history(self):
        with open(f"chats/{self.chat_id}.json", "w", encoding="utf-8") as f:
            json.dump(self.messages, f, ensure_ascii=False, indent=2)
        self.load_chat_list()

    def load_chat_list(self):
        self.chat_list.clear()
        for file in os.listdir("chats"):
            if file.endswith(".json"):
                item = QListWidgetItem(file.replace(".json", ""))
                self.chat_list.addItem(item)

    def load_selected_chat(self, item):
        chat_id = item.text()
        self.chat_id = chat_id
        self.messages = []
        try:
            with open(f"chats/{chat_id}.json", "r", encoding="utf-8") as f:
                self.messages = json.load(f)
        except Exception:
            pass

        for i in reversed(range(self.chat_layout.count() - 1)):
            widget = self.chat_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        for msg in self.messages:
            if msg["role"] != "system":
                self.add_message(msg["content"], is_user=(msg["role"] == "user"))

    def create_new_chat(self):
        self.chat_id = str(uuid.uuid4())
        self.messages = [{"role": "system", "content": "Jesteś pomocnym asystentem."}]
        for i in reversed(range(self.chat_layout.count() - 1)):
            widget = self.chat_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self.save_history()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatWidget()
    window.show()
    sys.exit(app.exec_())
