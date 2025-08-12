import os
from time import localtime
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtGui import QIcon
import subprocess
import platform
from datetime import date
import requests, base64


logo_path = os.path.join(os.path.dirname(__file__), "logo", "logo.ico")


class BoletoApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Verificador de Boletos")
        self.setWindowIcon(QIcon(logo_path))
        self.setFixedSize(420, 400)
        self.path_json = os.path.join(os.path.dirname(__file__), "path.json")
        self.default_folder_path = r"C:\Users\CENTRO AUTOMOTIVO\Documents\BoletosJapa"
        self.folder_path = self.load_last_path()
        self.setup_ui()
    def load_last_path(self):
        import json
        if os.path.exists(self.path_json):
            try:
                with open(self.path_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    folder_path = data.get("folder_path", self.default_folder_path)
                    if folder_path:
                        return folder_path
            except Exception:
                pass
        return self.default_folder_path

    def save_last_path(self, path):
        import json
        try:
            with open(self.path_json, "w", encoding="utf-8") as f:
                json.dump({"folder_path": path}, f)
        except Exception:
            pass
    
    def send_via_whatsapp(self):
        
        selected_item = self.boleto_list.currentItem()
        if not selected_item:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione um boleto primeiro.")
            return

        filename = selected_item.data(QtCore.Qt.UserRole)
        full_path = os.path.join(self.folder_path, filename)

        # Perguntar número de telefone
        num, ok = QtWidgets.QInputDialog.getText(self, "Enviar via WhatsApp", "Digite o número com DDD (ex: 5511999999999):")
        if not ok or not num.strip():
            return

        # Ler e codificar arquivo
        try:
            with open(full_path, "rb") as f:
                file_data = f.read()
            file_b64 = base64.b64encode(file_data).decode("utf-8")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Não foi possível ler o arquivo.\n{e}")
            return

        # Configuração da Evolution API
        API_URL = "https://evoapi.onrender.com/message/sendMedia/japacenter"
        API_TOKEN = "SEU_TOKEN_AQUI"


        payload = {
            "number": num,
            "mediatype": "document",
            "caption": f"Boleto: {filename}",
            "fileName": filename,
            "file": file_b64
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_TOKEN}"
        }

        try:
            r = requests.post(API_URL, json=payload, headers=headers, timeout=20)
            if r.status_code == 200:
                QtWidgets.QMessageBox.information(self, "Sucesso", "Boleto enviado com sucesso!")
            else:
                QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao enviar boleto.\nCódigo: {r.status_code}\nResposta: {r.text}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Erro de conexão: {e}")


    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout()
        title = QtWidgets.QLabel(f"Boletos encontrados - {self.get_today()}")
        title.setFont(QtGui.QFont("Segoe UI", 14, QtGui.QFont.Bold))
        title.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title)
        self.show_paid_checkbox = QtWidgets.QCheckBox("Mostrar boletos pagos")
        self.show_paid_checkbox.setChecked(False)
        self.show_paid_checkbox.stateChanged.connect(self.load_boletos)
        layout.addWidget(self.show_paid_checkbox)
        refresh_btn = QtWidgets.QPushButton("Atualizar")
        send_btn = QtWidgets.QPushButton("Enviar via WhatsApp")
        send_btn.setIcon(QIcon(logo_path))
        send_btn.clicked.connect(self.send_via_whatsapp)
        layout.addWidget(send_btn)

        refresh_btn.setIcon(QIcon(logo_path))
        refresh_btn.clicked.connect(self.load_boletos)
        layout.addWidget(refresh_btn)
        self.boleto_list = QtWidgets.QListWidget()
        self.boleto_list.setStyleSheet("""
            QListWidget { font-size: 13pt; }
            QListWidget::item { padding: 10px; }
        """)
        self.boleto_list.itemClicked.connect(self.on_item_click)
        layout.addWidget(self.boleto_list)
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setFont(QtGui.QFont("Segoe UI", 12))
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.status_label)
        self.setLayout(layout)
        self.load_boletos()

    def get_today(self):
        t = localtime()
        return f"{t.tm_mday:02}_{t.tm_mon:02}_{t.tm_year}"

    def load_boletos(self):
        self.boleto_list.clear()
        if not os.path.exists(self.folder_path) or not os.listdir(self.folder_path):
            dlg = QtWidgets.QFileDialog(self)
            dlg.setFileMode(QtWidgets.QFileDialog.Directory)
            dlg.setWindowTitle("Selecione a pasta dos boletos")
            dlg.setOptions(QtWidgets.QFileDialog.ShowDirsOnly)
            if dlg.exec_():
                selected = dlg.selectedFiles()
                if selected:
                    self.folder_path = selected[0]
                    self.save_last_path(self.folder_path)
            else:
                self.status_label.setText("Nenhum boleto encontrado e nenhuma pasta selecionada.")
                self.status_label.setStyleSheet("")
                return

        today = self.get_today()
        today_tuple = tuple(map(int, today.split('_')))
        today_date = date(today_tuple[2], today_tuple[1], today_tuple[0])

        if not os.path.exists(self.folder_path):
            self.status_label.setText("Pasta não encontrada.")
            self.status_label.setStyleSheet("")
            return

        files = os.listdir(self.folder_path)
        encontrados = 0
        atrasados = 0
        pagos = 0
        show_paid = self.show_paid_checkbox.isChecked()

        import re
        for f in files:
            if not f.lower().startswith("boleto"):
                continue
            if not show_paid and "pago" in f.lower():
                continue
            match = re.search(r'(\d{2})_(\d{2})_(\d{4})', f)
            item_text = f"• {f}"
            color = None
            if match:
                boleto_day = int(match.group(1))
                boleto_month = int(match.group(2))
                boleto_year = int(match.group(3))
                boleto_date = date(boleto_year, boleto_month, boleto_day)
                if "pago" in f.lower():
                    pagos += 1
                    color = QtGui.QColor("#b6fcb6")
                elif boleto_date == today_date:
                    item_text = f"✅ {f}"
                    encontrados += 1
                    color = QtGui.QColor("#fffcb6")
                elif boleto_date < today_date and "pago" not in f.lower():
                    item_text = f"⚠️ {f} (atrasado)"
                    atrasados += 1
                    color = QtGui.QColor("#ffb6b6")
            item = QtWidgets.QListWidgetItem(item_text)
            item.setData(QtCore.Qt.UserRole, f)
            if color:
                item.setBackground(color)
            self.boleto_list.addItem(item)

        status = []
        if encontrados:
            status.append(f"{encontrados} boleto(s) vencem hoje.")
        if atrasados:
            status.append(f"{atrasados} boleto(s) atrasado(s).")
        if show_paid and pagos:
            status.append(f"{pagos} boleto(s) pago(s).")
        if not status:
            status.append("Nenhum boleto vencendo hoje.")
        self.status_label.setText(" ".join(status))
        self.status_label.setStyleSheet("")

    def on_item_click(self, item):
        filename = item.data(QtCore.Qt.UserRole)
        full_path = os.path.join(self.folder_path, filename)
        print(full_path)
        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle("Abrir boleto")
        msg.setTextFormat(QtCore.Qt.RichText)
        msg.setText(f"Deseja abrir o arquivo:<br><b>{filename}</b>?")
        msg.setWindowIcon(QIcon(logo_path))
        msg.setStandardButtons(QtWidgets.QMessageBox.NoButton)
        btn_sim = msg.addButton("Sim", QtWidgets.QMessageBox.YesRole)
        btn_nao = msg.addButton("Não", QtWidgets.QMessageBox.NoRole)
        msg.exec_()
        if msg.clickedButton() == btn_sim:
            self.abrir_arquivo(full_path)

    def abrir_arquivo(self, path):
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.call(["open", path])
        else:
            subprocess.call(["xdg-open", path])


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    window = BoletoApp()
    window.show()
    sys.exit(app.exec_())
    sys.exit(app.exec_())
