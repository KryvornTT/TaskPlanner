from datetime import datetime, timedelta
import sqlite3
from pathlib import Path

from kivy.lang import Builder
from kivy.metrics import dp
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText, MDIconButton
from kivymd.uix.dialog import MDDialog, MDDialogHeadlineText, MDDialogButtonContainer
from kivymd.uix.list import MDList, MDListItem, MDListItemHeadlineText, MDListItemTrailingCheckbox
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.pickers import MDModalDatePicker

KV = '''
MDBoxLayout:
    orientation: "vertical"
    md_bg_color: app.theme_cls.backgroundColor

    MDTopAppBar:
        title: "Планировщик задач"
        elevation: 2

    # Навигация по дням (стрелки + дата)
    MDBoxLayout:
        size_hint_y: None
        height: dp(50)
        padding: dp(8)
        spacing: dp(8)

        MDIconButton:
            icon: "chevron-left"
            on_release: app.change_day(-1)

        MDLabel:
            id: date_label
            text: "Сегодня"
            halign: "center"
            font_style: "Title"

        MDIconButton:
            icon: "chevron-right"
            on_release: app.change_day(1)

    # Кнопки "Сегодня" и Календарь по центру
    MDBoxLayout:
        size_hint_y: None
        height: dp(52)
        padding: [dp(20), 0, dp(20), dp(8)]
        spacing: dp(12)
        pos_hint: {"center_x": 0.5}

        MDButton:
            style: "filled"
            size_hint_x: 0.6
            on_release: app.go_today()
            MDButtonText:
                text: "Сегодня"

        MDIconButton:
            icon: "calendar"
            style: "filled"
            on_release: app.open_main_date_picker()

    MDScrollView:
        MDList:
            id: task_list
            padding: dp(10)

    MDButton:
        style: "filled"
        size_hint_y: None
        height: dp(48)
        pos_hint: {"center_x": 0.5}
        on_release: app.show_add_dialog()
        MDButtonText:
            text: "Добавить задачу"
'''

class Database:
    def __init__(self):
        self.path = Path(__file__).parent / "tasks.db"
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                task_date TEXT NOT NULL,
                is_done INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()

    def add_task(self, title, date):
        cur = self.conn.execute(
            "INSERT INTO tasks (title, task_date) VALUES (?, ?)",
            (title, date)
        )
        self.conn.commit()
        return cur.lastrowid

    def get_tasks(self, date):
        return self.conn.execute(
            "SELECT id, title, is_done FROM tasks WHERE task_date = ? ORDER BY id",
            (date,)
        ).fetchall()

    def toggle_done(self, task_id, is_done):
        self.conn.execute(
            "UPDATE tasks SET is_done = ? WHERE id = ?",
            (1 if is_done else 0, task_id)
        )
        self.conn.commit()

    def update_task(self, task_id, title, date):
        self.conn.execute(
            "UPDATE tasks SET title = ?, task_date = ? WHERE id = ?",
            (title, date, task_id)
        )
        self.conn.commit()

    def delete_task(self, task_id):
        self.conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()

class TaskApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = Database()
        self.current_date = datetime.now().date()
        self.selected_date = self.current_date
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"

    def build(self):
        return Builder.load_string(KV)

    def on_start(self):
        self.update_date_label()
        self.load_tasks()

    def update_date_label(self):
        today = datetime.now().date()
        if self.current_date == today:
            text = f"Сегодня — {self.current_date.strftime('%d.%m.%Y')}"
        else:
            text = self.current_date.strftime("%d.%m.%Y")
        self.root.ids.date_label.text = text

    def change_day(self, delta):
        self.current_date += timedelta(days=delta)
        self.update_date_label()
        self.load_tasks()

    def go_today(self):
        self.current_date = datetime.now().date()
        self.update_date_label()
        self.load_tasks()

    def open_main_date_picker(self):
        """Календарь на главном экране — переход на выбранную дату"""
        date_dialog = MDModalDatePicker()
        date_dialog.bind(on_ok=self.on_main_date_selected)
        date_dialog.open()

    def on_main_date_selected(self, instance):
        self.current_date = instance.get_date()[0]
        self.update_date_label()
        self.load_tasks()
        instance.dismiss()

    def load_tasks(self):
        task_list = self.root.ids.task_list
        task_list.clear_widgets()
        date_str = self.current_date.strftime("%Y-%m-%d")
        tasks = self.db.get_tasks(date_str)

        for i, (task_id, title, is_done) in enumerate(tasks, 1):
            self.add_task_item(task_id, title, bool(is_done), i)

    def add_task_item(self, task_id, title, is_done, number):
        text = f"{number}. {title}"
        if is_done:
            text = f"[s]{text}[/s]"

        checkbox = MDListItemTrailingCheckbox()
        checkbox.active = is_done

        item = MDListItem(
            MDListItemHeadlineText(text=text),
            checkbox,
        )

        item.task_id = task_id
        item.task_title = title
        item.task_date = self.current_date

        def on_check(instance, value):
            self.on_checkbox(task_id, value)

        checkbox.bind(active=on_check)

        edit_btn = MDIconButton(icon="pencil")
        edit_btn.bind(on_release=lambda x: self.edit_task(item))

        del_btn = MDIconButton(icon="delete")
        del_btn.bind(on_release=lambda x: self.delete_task(task_id))

        item.add_widget(edit_btn)
        item.add_widget(del_btn)

        self.root.ids.task_list.add_widget(item)

    def on_checkbox(self, task_id, value):
        self.db.toggle_done(task_id, value)
        self.load_tasks()

    def show_add_dialog(self):
        self.selected_date = self.current_date
        self._show_task_dialog(title="", is_edit=False)

    def edit_task(self, item):
        self.selected_date = item.task_date
        self.editing_task_id = item.task_id
        self._show_task_dialog(title=item.task_title, is_edit=True)

    def _show_task_dialog(self, title="", is_edit=False):
        self.title_field = MDTextField(
            text=title,
            hint_text="Название задачи",
            mode="outlined"
        )

        self.date_label = MDLabel(
            text=f"Дата: {self.selected_date.strftime('%d.%m.%Y')}",
            size_hint_y=None,
            height=dp(30)
        )

        date_btn = MDIconButton(
            icon="calendar",
            on_release=self.open_date_picker
        )

        date_box = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(40),
            spacing=dp(10)
        )
        date_box.add_widget(self.date_label)
        date_box.add_widget(date_btn)

        content = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            size_hint_y=None,
            height=dp(130),
            padding=dp(10)
        )
        content.add_widget(self.title_field)
        content.add_widget(date_box)

        dialog_title = "Редактировать задачу" if is_edit else "Новая задача"

        self.dialog = MDDialog(
            MDDialogHeadlineText(text=dialog_title),
            content,
            MDDialogButtonContainer(
                MDButton(
                    MDButtonText(text="Отмена"),
                    style="text",
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDButton(
                    MDButtonText(text="Сохранить"),
                    style="filled",
                    on_release=lambda x: self.save_task(is_edit)
                ),
                spacing="8dp",
            ),
        )
        self.dialog.open()

    def open_date_picker(self, *args):
        date_dialog = MDModalDatePicker()
        date_dialog.bind(on_ok=self.on_date_selected)
        date_dialog.open()

    def on_date_selected(self, instance):
        self.selected_date = instance.get_date()[0]
        self.date_label.text = f"Дата: {self.selected_date.strftime('%d.%m.%Y')}"
        instance.dismiss()

    def save_task(self, is_edit=False):
        title = self.title_field.text.strip()
        if not title:
            print("Введите название")
            return

        date_str = self.selected_date.strftime("%Y-%m-%d")

        if is_edit:
            self.db.update_task(self.editing_task_id, title, date_str)
            print("Задача обновлена")
        else:
            self.db.add_task(title, date_str)
            print("Задача добавлена")

        self.dialog.dismiss()
        self.load_tasks()

    def delete_task(self, task_id):
        self.db.delete_task(task_id)
        self.load_tasks()
        print("Удалено")

if __name__ == "__main__":
    app = TaskApp()
    app.run()
