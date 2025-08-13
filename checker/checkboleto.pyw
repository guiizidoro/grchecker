import os
from time import localtime
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtGui import QIcon
import subprocess
import platform
from datetime import date
import requests, base64, json, re

logo_path = os.path.join(os.path.dirname(__file__), "logo", "logo.ico")
contacts_file = os.path.join(os.path.dirname(__file__), "contacts.json")

class ContactManager(QtWidgets.QDialog):
    def __init__(self, contacts, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gerenciar Contatos")
        self.setFixedSize(300, 400)
        self.contacts = contacts
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.contact_list = QtWidgets.QListWidget()
        self.load_contacts()
        layout.addWidget(self.contact_list)

        self.name_input = QtWidgets.QLineEdit()
        self.name_input.setPlaceholderText("Nome")
        layout.addWidget(self.name_input)

        self.number_input = QtWidgets.QLineEdit()
        self.number_input.setPlaceholderText("Somente número, sem traços.(Com DDD)")
        layout.addWidget(self.number_input)

        add_btn = QtWidgets.QPushButton("Adicionar / Atualizar")
        add_btn.clicked.connect(self.add_contact)
        layout.addWidget(add_btn)

        delete_btn = QtWidgets.QPushButton("Excluir Selecionado")
        delete_btn.clicked.connect(self.delete_contact)
        layout.addWidget(delete_btn)

        self.setLayout(layout)

    def load_contacts(self):
        self.contact_list.clear()
        for name, number in self.contacts.items():
            self.contact_list.addItem(f"{name}: {number}")

    def add_contact(self):
        name = self.name_input.text().strip()
        number = self.number_input.text().strip()
        if name and number:
            if not number[:2] == "55":
                self.contacts[name] = f"55{number}"
            else:
                self.contacts[name] = number
            self.load_contacts()
            self.name_input.clear()
            self.number_input.clear()

    def delete_contact(self):
        selected = self.contact_list.currentItem()
        if selected:
            name = selected.text().split(":")[0]
            if name in self.contacts:
                del self.contacts[name]
                self.load_contacts()


class BoletoApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Verificador de Boletos")
        self.setWindowIcon(QIcon(logo_path))
        self.setFixedSize(420, 450)
        self.path_json = os.path.join(os.path.dirname(__file__), "path.json")
        self.default_folder_path = r"C:\\Users\\CENTRO AUTOMOTIVO\\Documents\\BoletosJapa"
        self.folder_path = self.load_last_path()
        self.load_contacts()
        self.setup_ui()

    
    def load_contacts(self):
        if os.path.exists(contacts_file):
            try:
                with open(contacts_file, "r", encoding="utf-8") as f:
                    self.contacts = json.load(f)
            except:
                self.contacts = {}
        else:
            self.contacts = {}

    def save_contacts(self):
        try:
            with open(contacts_file, "w", encoding="utf-8") as f:
                json.dump(self.contacts, f, indent=2, ensure_ascii=False)
        except:
            pass

    def load_last_path(self):
        if os.path.exists(self.path_json):
            try:
                with open(self.path_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("folder_path", self.default_folder_path)
            except:
                pass
        return self.default_folder_path

    def save_last_path(self, path):
        try:
            with open(self.path_json, "w", encoding="utf-8") as f:
                json.dump({"folder_path": path}, f)
        except:
            pass

    def open_contact_manager(self):
        dlg = ContactManager(self.contacts, self)
        dlg.exec_()
        self.save_contacts()

    def send_via_whatsapp(self):
        selected_item = self.boleto_list.currentItem()
        if not selected_item:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione um boleto primeiro.")
            return

        filename = selected_item.data(QtCore.Qt.UserRole)
        full_path = os.path.join(self.folder_path, filename)

        names = list(self.contacts.keys())
        name, ok = QtWidgets.QInputDialog.getItem(self, "Escolher Contato", "Contato:", names, 0, True)
        if not ok or not name.strip():
            return

        number = self.contacts.get(name.strip())
        if not number:
            QtWidgets.QMessageBox.warning(self, "Erro", "Número não encontrado para o contato.")
            return

        try:
            with open(full_path, "rb") as f:
                file_data = f.read()
            file_b64 = base64.b64encode(file_data).decode("utf-8")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Erro ao ler o arquivo: {e}")
            return

        API_URL = "https://evolution-api-ny08.onrender.com/message/sendMedia/japacenter"
        API_TOKEN = "91910192"

        payload = {
            "number": number,
            "options": {"delay": 123, "presence": "composing"},
            "mediaMessage": {
                "mediatype": "document",
                "fileName": filename,
                "caption": f"Boleto: {filename}",
                "media": file_b64
            }
        }
        headers = {"Content-Type": "application/json", "apikey": API_TOKEN}

        try:
            r = requests.post(API_URL, json=payload, headers=headers, timeout=20)
            if r.status_code in (200, 201):
                QtWidgets.QMessageBox.information(self, "Sucesso", "Boleto enviado com sucesso!")
            else:
                QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao enviar.\n{r.status_code}: {r.text}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Erro de conexão: {e}")

    def select_folder(self):
        dlg = QtWidgets.QFileDialog(self)
        dlg.setFileMode(QtWidgets.QFileDialog.Directory)
        dlg.setWindowTitle("Selecione a pasta dos boletos")
        dlg.setOptions(QtWidgets.QFileDialog.ShowDirsOnly)
        if dlg.exec_():
            selected = dlg.selectedFiles()
            if selected:
                new_folder = selected[0]
                if self.has_boletos_in_folder(new_folder):
                    self.folder_path = new_folder
                    self.save_last_path(new_folder)
                    self.load_boletos()
                else:
                    QtWidgets.QMessageBox.warning(self, "Aviso", "A pasta selecionada não contém boletos válidos.")


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

        btn_layout = QtWidgets.QHBoxLayout()
        refresh_btn = QtWidgets.QPushButton("Atualizar")
        refresh_btn.setIcon(QIcon(logo_path))
        refresh_btn.clicked.connect(self.load_boletos)
        btn_layout.addWidget(refresh_btn)

        select_folder_btn = QtWidgets.QPushButton("Selecionar Pasta")
        select_folder_btn.clicked.connect(self.select_folder)
        btn_layout.addWidget(select_folder_btn)


        contact_btn = QtWidgets.QPushButton("Contatos")
        contact_btn.clicked.connect(self.open_contact_manager)
        btn_layout.addWidget(contact_btn)
        layout.addLayout(btn_layout)

        send_btn = QtWidgets.QPushButton("Enviar via WhatsApp")
        send_btn.setIcon(QIcon(logo_path))
        send_btn.clicked.connect(self.send_via_whatsapp)
        layout.addWidget(send_btn)

        self.boleto_list = QtWidgets.QListWidget()
        self.boleto_list.setStyleSheet("QListWidget { font-size: 13pt; } QListWidget::item { padding: 10px; }")
        self.boleto_list.itemClicked.connect(self.on_item_selected)
        self.boleto_list.itemDoubleClicked.connect(self.on_item_double_click)
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

    def has_boletos_in_folder(self, folder_path):
        if not os.path.exists(folder_path):
            return False
        try:
            files = os.listdir(folder_path)
            for f in files:
                if f.lower().startswith("boleto"):
                    return True
            return False
        except Exception:
            return False

    def load_boletos(self):
        self.boleto_list.clear()


        if not self.has_boletos_in_folder(self.folder_path):
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
                return

        today = self.get_today()
        today_tuple = tuple(map(int, today.split('_')))
        today_date = date(today_tuple[2], today_tuple[1], today_tuple[0])
        files = os.listdir(self.folder_path)

        encontrados = atrasados = pagos = 0
        show_paid = self.show_paid_checkbox.isChecked()

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


    def on_item_selected(self, item):
        pass

    def on_item_double_click(self, item):
        filename = item.data(QtCore.Qt.UserRole)
        full_path = os.path.join(self.folder_path, filename)
        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle("Abrir boleto")
        msg.setTextFormat(QtCore.Qt.RichText)
        msg.setText(f"Deseja abrir o arquivo:<br><b>{filename}</b>?")
        msg.setWindowIcon(QIcon(logo_path))
        msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if msg.exec_() == QtWidgets.QMessageBox.Yes:
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
