import traceback
import json
import math
from datetime import datetime
from tkinter import font as tkfont
from PIL import Image, ImageTk
import pandas as pd
import io
import base64
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
import tempfile
import shutil
from PIL import Image, ImageTk, ImageEnhance
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import os
import sys

# Проверка необходимых модулей
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Предупреждение: PIL не установлен. Функции изображений недоступны.")
    print("Установите: pip install Pillow")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Предупреждение: pandas не установлен. Функции Excel недоступны.")
    print("Установите: pip install pandas")

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    print("Предупреждение: openpyxl не установлен. Экспорт в Excel недоступен.")
    print("Установите: pip install openpyxl")

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("Предупреждение: reportlab не установлен. Функции печати недоступны.")
    print("Установите: pip install reportlab")

import io
import base64
import tempfile

# Установка правильной кодировки
if sys.platform.startswith('win'):
    os.system('chcp 65001 > nul')  # UTF-8 для Windows


class ModernDatabaseApp:
    def __init__(self, root):
        self.image_columns = []  # Список колонок с изображениями
        self.photo_cache = {}  # Кэш для миниатюр
        self.root = root
        self.root.title("SQLite3 Database Manager - Modern")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f5f5f5')

        # Настройка горячих клавиш
        self.setup_hotkeys()

        # Настройка стилей
        self.setup_styles()

        # Переменные
        self.db_name = None
        self.current_table = None
        self.connection = None
        self.joined_tables = []
        self.selected_attributes = []
        self.table_joins = {}
        self.image_references = []

        self.create_widgets()
        self.select_database_file()

    def setup_hotkeys(self):
        """Настройка горячих клавиш"""
        self.root.bind('<Return>', self.on_enter_key)
        self.root.bind('<Control-s>', self.quick_save)
        self.root.bind('<Control-o>', self.quick_open)
        self.root.bind('<F5>', self.quick_refresh)
        self.root.bind('<Delete>', self.quick_delete)
        self.root.bind('<Control-p>', self.quick_print)

    def on_enter_key(self, event):
        """Обработка клавиши Enter"""
        focused_widget = self.root.focus_get()

        # Если фокус в диалоговом окне - нажать OK
        if isinstance(focused_widget, (tk.Toplevel, tk.simpledialog.Dialog)):
            for widget in focused_widget.winfo_children():
                if isinstance(widget, ttk.Button) and widget['text'] in ['✅ OK', '✅ Сохранить', '✅ Добавить',
                                                                         '✅ Применить']:
                    widget.invoke()
                    return "break"

        # Если фокус в основном окне - обновить данные
        elif self.current_table:
            self.refresh_data()
            return "break"

    def quick_save(self, event=None):
        """Быстрое сохранение"""
        if self.connection:
            self.connection.commit()
            self.update_status("💾 Данные сохранены!")
        return "break"

    def quick_open(self, event=None):
        """Быстрое открытие БД"""
        self.change_database()
        return "break"

    def quick_refresh(self, event=None):
        """Быстрое обновление"""
        self.refresh_data()
        return "break"

    def quick_delete(self, event=None):
        """Быстрое удаление"""
        if self.tree.selection():
            self.delete_record()
        return "break"

    def quick_print(self, event=None):
        """Быстрая печать"""
        self.print_data()
        return "break"

    def setup_styles(self):
        """Настройка современных стилей"""
        style = ttk.Style()
        style.theme_use('clam')

        # Кастомные стили
        style.configure('Modern.TFrame', background='#f5f5f5')
        style.configure('Modern.TLabelframe', background='#ffffff', bordercolor='#e0e0e0')
        style.configure('Modern.TLabelframe.Label', background='#ffffff', foreground='#333333')

        style.configure('Primary.TButton', background='#007acc', foreground='white', borderwidth=0)
        style.configure('Secondary.TButton', background='#6c757d', foreground='white', borderwidth=0)
        style.configure('Success.TButton', background='#28a745', foreground='white', borderwidth=0)
        style.configure('Danger.TButton', background='#dc3545', foreground='white', borderwidth=0)
        style.configure('Warning.TButton', background='#ffc107', foreground='#333333', borderwidth=0)

        style.configure('Modern.Treeview', background='#ffffff', foreground='#333333', fieldbackground='#ffffff')
        style.configure('Modern.Treeview.Heading', background='#007acc', foreground='white', relief='flat')

        style.map('Modern.Treeview.Heading', background=[('active', '#005a9e')])
        style.map('Primary.TButton', background=[('active', '#005a9e')])
        style.map('Secondary.TButton', background=[('active', '#545b62')])
        style.map('Success.TButton', background=[('active', '#218838')])
        style.map('Danger.TButton', background=[('active', '#c82333')])

        style.configure('Title.TLabel', background='#f5f5f5', foreground='#333333', font=('Segoe UI', 12, 'bold'))
        style.configure('Subtitle.TLabel', background='#f5f5f5', foreground='#666666', font=('Segoe UI', 10))

    def create_widgets(self):
        """Создание современных элементов интерфейса"""
        # Главный контейнер
        main_container = ttk.Frame(self.root, style='Modern.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Заголовок приложения
        header_frame = ttk.Frame(main_container, style='Modern.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 20))

        title_label = ttk.Label(header_frame, text="🗃️ SQLite Database Manager",
                                style='Title.TLabel', font=('Segoe UI', 16, 'bold'))
        title_label.pack(side=tk.LEFT)

        # Подсказки горячих клавиш
        hotkeys_label = ttk.Label(header_frame,
                                  text="🔥 Горячие клавиши: Enter=Обновить, Ctrl+S=Сохранить, Del=Удалить, F5=Обновить, Ctrl+P=Печать",
                                  style='Subtitle.TLabel', font=('Segoe UI', 8))
        hotkeys_label.pack(side=tk.LEFT, padx=20)

        self.db_label = ttk.Label(header_frame, text="📁 База данных: не выбрана",
                                  style='Subtitle.TLabel')
        self.db_label.pack(side=tk.RIGHT)

        # Панель быстрых действий
        quick_actions_frame = ttk.LabelFrame(main_container, text="🚀 Быстрые действия",
                                             style='Modern.TLabelframe', padding=15)
        quick_actions_frame.pack(fill=tk.X, pady=(0, 20))

        actions_grid = ttk.Frame(quick_actions_frame, style='Modern.TFrame')
        actions_grid.pack(fill=tk.X)

        actions = [
            ("📊 Создать таблицу", self.create_table_dialog, 'Primary.TButton'),
            ("➕ Добавить запись", self.add_record_dialog, 'Success.TButton'),
            ("🗑️ Удалить таблицу", self.delete_table, 'Danger.TButton'),
            ("🔄 Обновить данные", self.refresh_data, 'Secondary.TButton'),
            ("🔗 Быстрое соединение", self.quick_join_tables, 'Primary.TButton'),
            ("👁️ Выбрать атрибуты", self.select_attributes_dialog, 'Secondary.TButton'),
            ("💾 Сменить БД", self.change_database, 'Secondary.TButton'),
            ("📝 Добавить колонку", self.add_column_dialog, 'Primary.TButton'),
            ("🖼️ Импорт Excel", self.import_excel, 'Success.TButton'),
            ("📤 Экспорт Excel", self.export_excel, 'Primary.TButton'),
            ("🖼️ Экспорт Excel с фото", self.export_excel_with_images_embedded, 'Success.TButton'),
            ("🖨️ Печать", self.print_data, 'Warning.TButton'),
            ("🔍 Исследовать БД", self.inspect_database, 'Primary.TButton'),
            ("🖼️ Найти все фото", self.find_and_display_all_photos, 'Success.TButton'),
            ("📷 Проверить фото", self.check_and_display_photos, 'Primary.TButton')
        ]

        for i, (text, command, style_name) in enumerate(actions):
            btn = ttk.Button(actions_grid, text=text, command=command, style=style_name)
            btn.grid(row=i // 4, column=i % 4, padx=5, pady=5, sticky='ew')
            actions_grid.columnconfigure(i % 4, weight=1)

        # Основной контент
        content_frame = ttk.Frame(main_container, style='Modern.TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Левая панель
        left_panel = ttk.Frame(content_frame, style='Modern.TFrame', width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        left_panel.pack_propagate(False)

        # Список таблиц
        tables_frame = ttk.LabelFrame(left_panel, text="📋 Таблицы базы данных",
                                      style='Modern.TLabelframe', padding=10)
        tables_frame.pack(fill=tk.BOTH, pady=(0, 15))

        search_frame = ttk.Frame(tables_frame, style='Modern.TFrame')
        search_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(search_frame, text="🔍 Поиск:", style='Subtitle.TLabel').pack(side=tk.LEFT)
        self.table_search = ttk.Entry(search_frame, style='Modern.TEntry', width=15)
        self.table_search.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        self.table_search.bind('<KeyRelease>', self.filter_tables)

        table_list_container = ttk.Frame(tables_frame, style='Modern.TFrame')
        table_list_container.pack(fill=tk.BOTH, expand=True)

        self.table_listbox = tk.Listbox(table_list_container, bg='white', bd=0,
                                        font=('Segoe UI', 9), highlightthickness=0)
        self.table_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        table_scrollbar = ttk.Scrollbar(table_list_container, orient=tk.VERTICAL)
        table_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.table_listbox.config(yscrollcommand=table_scrollbar.set)
        table_scrollbar.config(command=self.table_listbox.yview)
        self.table_listbox.bind('<<ListboxSelect>>', self.on_table_select)

        # Панель соединений
        joins_frame = ttk.LabelFrame(left_panel, text="🔗 Активные соединения",
                                     style='Modern.TLabelframe', padding=10)
        joins_frame.pack(fill=tk.BOTH, expand=True)

        self.join_info_text = tk.Text(joins_frame, height=8, bg='white', bd=0,
                                      font=('Segoe UI', 9), padx=10, pady=10)
        self.join_info_text.pack(fill=tk.BOTH, expand=True)

        join_buttons_frame = ttk.Frame(joins_frame, style='Modern.TFrame')
        join_buttons_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(join_buttons_frame, text="🗑️ Очистить все", command=self.clear_joins,
                   style='Danger.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(join_buttons_frame, text="✂️ Удалить", command=self.remove_join,
                   style='Secondary.TButton').pack(side=tk.LEFT)
        ttk.Button(join_buttons_frame, text="⚙️ Расширенное", command=self.join_tables_dialog,
                   style='Primary.TButton').pack(side=tk.LEFT, padx=(5, 0))

        # Правая панель
        right_panel = ttk.Frame(content_frame, style='Modern.TFrame')
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Панель инструментов данных
        data_tools_frame = ttk.LabelFrame(right_panel, text="📊 Данные таблицы",
                                          style='Modern.TLabelframe', padding=10)
        data_tools_frame.pack(fill=tk.X, pady=(0, 15))

        sort_filter_frame = ttk.Frame(data_tools_frame, style='Modern.TFrame')
        sort_filter_frame.pack(fill=tk.X, pady=(0, 10))

        # Сортировка
        sort_frame = ttk.Frame(sort_filter_frame, style='Modern.TFrame')
        sort_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(sort_frame, text="Сортировка:", style='Subtitle.TLabel').pack(anchor=tk.W)

        sort_controls = ttk.Frame(sort_frame, style='Modern.TFrame')
        sort_controls.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(sort_controls, text="По:", style='Subtitle.TLabel').pack(side=tk.LEFT)
        self.sort_column = ttk.Combobox(sort_controls, state="readonly", width=15)
        self.sort_column.pack(side=tk.LEFT, padx=5)

        self.sort_order = ttk.Combobox(sort_controls, values=["По возрастанию", "По убыванию"],
                                       state="readonly", width=15)
        self.sort_order.set("По возрастанию")
        self.sort_order.pack(side=tk.LEFT, padx=5)

        ttk.Button(sort_controls, text="🔄 Применить", command=self.apply_sorting,
                   style='Primary.TButton').pack(side=tk.LEFT, padx=5)

        # Информация об атрибутах
        attributes_frame = ttk.Frame(data_tools_frame, style='Modern.TFrame')
        attributes_frame.pack(fill=tk.X, pady=(0, 10))

        self.attributes_label = ttk.Label(attributes_frame,
                                          text="👁️ Отображаемые атрибуты: все",
                                          style='Subtitle.TLabel')
        self.attributes_label.pack(anchor=tk.W)

        # Кнопки редактирования
        edit_buttons_frame = ttk.Frame(data_tools_frame, style='Modern.TFrame')
        edit_buttons_frame.pack(fill=tk.X)

        ttk.Button(edit_buttons_frame, text="✏️ Редактировать", command=self.edit_cell_value,
                   style='Primary.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(edit_buttons_frame, text="🗑️ Удалить запись", command=self.delete_record,
                   style='Danger.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(edit_buttons_frame, text="📝 Переименовать атрибут",
                   command=self.rename_attribute_dialog, style='Secondary.TButton').pack(side=tk.LEFT)

        # Таблица данных с улучшенной прокруткой
        data_frame = ttk.Frame(right_panel, style='Modern.TFrame')
        data_frame.pack(fill=tk.BOTH, expand=True)

        self.create_modern_treeview(data_frame)

        # Статус бар
        self.status_bar = ttk.Label(main_container, text="✅ Готов к работе",
                                    relief=tk.SUNKEN, style='Subtitle.TLabel')
        self.status_bar.pack(fill=tk.X, pady=(10, 0))

    def create_modern_treeview(self, parent):
        """Создание современного Treeview с улучшенной прокруткой"""
        table_container = ttk.Frame(parent, style='Modern.TFrame')
        table_container.pack(fill=tk.BOTH, expand=True)

        # Создаем фрейм для таблицы с прокруткой
        tree_frame = ttk.Frame(table_container, style='Modern.TFrame')
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Создаем Treeview
        self.tree = ttk.Treeview(tree_frame, style='Modern.Treeview',
                                 show='headings', selectmode='browse')

        # Вертикальная прокрутка
        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=v_scrollbar.set)

        # Горизонтальная прокрутка
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=h_scrollbar.set)

        # Размещаем элементы
        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')

        # Настройка весов для расширения
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.create_context_menu()

    def filter_tables(self, event):
        """Фильтрация списка таблиц"""
        search_term = self.table_search.get().lower()
        current_selection = self.table_listbox.curselection()
        current_table = None
        if current_selection:
            current_table = self.table_listbox.get(current_selection[0])

        self.table_listbox.delete(0, tk.END)

        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()

            for table in tables:
                table_name = table[0]
                if table_name != "sqlite_sequence" and search_term in table_name.lower():
                    self.table_listbox.insert(tk.END, table_name)
                    if table_name == current_table:
                        self.table_listbox.selection_set(tk.END)
        except sqlite3.Error:
            pass

    def update_status(self, message):
        """Обновление статус бара"""
        self.status_bar.config(text=message)
        self.root.after(3000, lambda: self.status_bar.config(text="✅ Готов к работе"))

    def select_database_file(self):
        file_path = filedialog.asksaveasfilename(
            title="Выберите файл базы данных",
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db"), ("All files", "*.*")]
        )

        if file_path:
            self.db_name = file_path
            self.connect_to_db()
        else:
            self.db_name = "my_database.db"
            self.connect_to_db()

    def connect_to_db(self):
        try:
            self.connection = sqlite3.connect(self.db_name)
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.update_table_list()
            self.update_db_label()
            self.update_status(f"✅ Подключено к базе данных: {os.path.basename(self.db_name)}")
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка подключения: {e}")

    def change_database(self):
        if messagebox.askyesno("Смена базы данных",
                               "Вы уверены, что хотите сменить базу данных?"):
            if self.connection:
                self.connection.close()
            self.select_database_file()

    def update_table_list(self):
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()

            self.table_listbox.delete(0, tk.END)
            for table in tables:
                if table[0] != "sqlite_sequence":
                    self.table_listbox.insert(tk.END, table[0])
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка получения списка таблиц: {e}")

    def on_table_select(self, event):
        selection = self.table_listbox.curselection()
        if selection:
            new_table = self.table_listbox.get(selection[0])

            if self.current_table and self.joined_tables:
                self.table_joins[self.current_table] = self.joined_tables.copy()

            self.current_table = new_table
            self.joined_tables = self.table_joins.get(self.current_table, [])
            self.selected_attributes.clear()
            self.update_join_info()
            self.update_attributes_label()
            self.display_table_data()
            self.update_status(f"📊 Выбрана таблица: {new_table}")

    def delete_table(self):
        if not self.current_table:
            messagebox.showwarning("Предупреждение", "Выберите таблицу для удаления!")
            return

        if messagebox.askyesno("Подтверждение",
                               f"Вы уверены, что хотите удалить таблицу '{self.current_table}'?"):
            try:
                cursor = self.connection.cursor()
                cursor.execute(f"DROP TABLE IF EXISTS {self.escape_table_name(self.current_table)}")
                self.connection.commit()

                self.update_status(f"✅ Таблица '{self.current_table}' удалена!")
                self.current_table = None
                self.joined_tables.clear()
                self.selected_attributes.clear()
                if self.current_table in self.table_joins:
                    del self.table_joins[self.current_table]
                self.update_table_list()
                self.clear_treeview()
                self.update_join_info()
                self.update_attributes_label()

            except sqlite3.Error as e:
                messagebox.showerror("Ошибка", f"Ошибка удаления таблицы: {e}")

    def add_photo_dialog(self, column_name, table_name, item=None, col_index=None):
        """Диалог для добавления фотографии"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Добавить фото - {column_name}")
        dialog.geometry("500x400")
        dialog.configure(bg='#f5f5f5')
        dialog.transient(self.root)
        dialog.grab_set()

        main_frame = ttk.Frame(dialog, style='Modern.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text="📸 Добавление фотографии",
                  font=('Segoe UI', 14, 'bold')).pack(pady=10)

        # Область предпросмотра
        preview_frame = ttk.LabelFrame(main_frame, text="Предпросмотр", style='Modern.TLabelframe')
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        preview_label = ttk.Label(preview_frame, text="Выберите изображение для предпросмотра",
                                  style='Subtitle.TLabel')
        preview_label.pack(pady=20)

        self.current_photo_data = None

        def load_image():
            file_path = filedialog.askopenfilename(
                title="Выберите изображение",
                filetypes=[
                    ("Изображения", "*.png *.jpg *.jpeg *.gif *.bmp"),
                    ("Все файлы", "*.*")
                ]
            )
            if file_path:
                try:
                    # Загружаем и обрабатываем изображение
                    with open(file_path, 'rb') as f:
                        self.current_photo_data = f.read()

                    # Показываем предпросмотр
                    image = Image.open(io.BytesIO(self.current_photo_data))
                    image.thumbnail((300, 300))
                    photo = ImageTk.PhotoImage(image)

                    preview_label.configure(image=photo, text="")
                    preview_label.image = photo

                    # Информация о файле
                    file_info = f"Файл: {os.path.basename(file_path)}\nРазмер: {len(self.current_photo_data)} байт"
                    info_label.config(text=file_info)

                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось загрузить изображение: {e}")

        def save_photo():
            if self.current_photo_data and item is not None:
                self.update_image_value(item, col_index, self.current_photo_data, column_name, table_name)
                dialog.destroy()
            elif self.current_photo_data:
                # Возвращаем данные фото
                self.photo_result = self.current_photo_data
                dialog.destroy()
            else:
                messagebox.showwarning("Предупреждение", "Сначала выберите изображение!")

        # Кнопки
        button_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="📁 Выбрать файл", command=load_image,
                   style='Primary.TButton').pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="✅ Сохранить фото", command=save_photo,
                   style='Success.TButton').pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="❌ Отмена", command=dialog.destroy,
                   style='Secondary.TButton').pack(side=tk.LEFT, padx=5)

        # Информация о файле
        info_label = ttk.Label(main_frame, text="", style='Subtitle.TLabel')
        info_label.pack(pady=5)

        # Подсказки
        tips_label = ttk.Label(main_frame,
                               text="💡 Поддерживаемые форматы: PNG, JPG, JPEG, GIF, BMP\n💡 Рекомендуемый размер: до 5 МБ",
                               font=('Segoe UI', 8), foreground="gray")
        tips_label.pack(pady=5)

        # Привязываем Enter к сохранению
        dialog.bind('<Return>', lambda e: save_photo())

        self.root.wait_window(dialog)
        return getattr(self, 'photo_result', None)

    def display_table_data(self, sort_column=None, sort_order="ASC"):
        if not self.current_table and not self.joined_tables:
            return

        try:
            self.clear_treeview()
            query, display_columns = self.build_query(sort_column, sort_order)

            if not display_columns:
                messagebox.showwarning("Предупреждение", "Нет атрибутов для отображения!")
                return

            # Настраиваем Treeview
            self.tree['columns'] = display_columns

            # Определяем, какие колонки содержат фото
            self.image_columns = []
            for col in display_columns:
                self.tree.heading(col, text=col)
                if self.is_image_column(col):
                    self.image_columns.append(col)
                    self.tree.column(col, width=150, minwidth=150, stretch=False)
                else:
                    self.tree.column(col, width=120, minwidth=80, stretch=True)

            available_columns = self.get_available_columns()
            self.sort_column['values'] = available_columns
            if available_columns:
                self.sort_column.set(available_columns[0])

            cursor = self.connection.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()

            # Получаем первичный ключ таблицы для последующего доступа к фото
            primary_key = None
            if self.current_table:
                cursor.execute(f"PRAGMA table_info({self.escape_table_name(self.current_table)})")
                columns_info = cursor.fetchall()
                if columns_info:
                    primary_key = columns_info[0][1]

            # Создаем миниатюры фото
            self.photo_cache = {}  # Кэш для миниатюр
            for row_index, row in enumerate(rows):
                formatted_row = self.format_row_for_display(row, display_columns)
                item_id = self.tree.insert("", tk.END, values=formatted_row)

                # Если есть фото-колонки, добавляем миниатюры
                for col_index, col_name in enumerate(display_columns):
                    if col_name in self.image_columns and row[col_index] is not None:
                        try:
                            # Создаем миниатюру фото
                            image_data = row[col_index]
                            if isinstance(image_data, bytes) and len(image_data) > 100:
                                # Создаем уникальный ключ для кэша
                                cache_key = f"{primary_key}_{row_index}_{col_name}"
                                if cache_key not in self.photo_cache:
                                    image = Image.open(io.BytesIO(image_data))
                                    image.thumbnail((100, 100))
                                    photo = ImageTk.PhotoImage(image)
                                    self.photo_cache[cache_key] = photo

                                # Получаем фото из кэша
                                photo = self.photo_cache[cache_key]

                                # Создаем кнопку с миниатюрой
                                btn = ttk.Button(self.tree, image=photo, width=100,
                                                 command=lambda d=image_data, c=col_name, pk=primary_key, r=row[0]:
                                                 self.view_image_with_info(c, d, pk, r))
                                btn.image = photo  # Сохраняем ссылку

                                # Встраиваем кнопку в ячейку Treeview
                                self.tree.window_create(item_id, column=col_index, window=btn)
                        except Exception as e:
                            print(f"Ошибка создания миниатюры: {e}")
                            # В случае ошибки отображаем текст
                            self.tree.set(item_id, col_name, "🖼️ Фото")

            # После загрузки данных проверяем фото
            self.check_and_display_photos()

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка загрузки данных: {e}")

    def is_image_column(self, column_name):
        """Проверяет, является ли колонка колонкой с изображениями"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({self.escape_table_name(self.current_table)})")
            columns = cursor.fetchall()

            for col in columns:
                if col[1] == column_name and col[2].upper() == 'BLOB':
                    return True

            # Проверяем соединенные таблицы
            for join_info in self.joined_tables:
                table_name = join_info['table2']
                cursor.execute(f"PRAGMA table_info({self.escape_table_name(table_name)})")
                columns = cursor.fetchall()

                for col in columns:
                    if col[1] == column_name and col[2].upper() == 'BLOB':
                        return True

        except sqlite3.Error:
            pass

        return False

    def format_row_for_display(self, row, display_columns):
        """Форматирует строку для отображения"""
        formatted_row = []

        for i, value in enumerate(row):
            col_name = display_columns[i]

            if value is None:
                formatted_row.append("")
            elif col_name in self.image_columns and isinstance(value, bytes):
                # Для фото-колонок оставляем пустое значение, т.к. будем встраивать кнопку
                formatted_row.append("")
            elif isinstance(value, bool):
                formatted_row.append("✅ Да" if value else "❌ Нет")
            elif isinstance(value, (int, float)):
                formatted_row.append(str(value))
            else:
                # Обрезаем длинный текст
                text = str(value)
                if len(text) > 50:
                    text = text[:47] + "..."
                formatted_row.append(text)

        return formatted_row

    def is_valid_image_blob(self, data):
        """Проверяет, являются ли данные валидным изображением"""
        if not isinstance(data, bytes):
            return False

        if len(data) < 100:  # Минимальный размер для изображения
            return False

        try:
            # Проверяем магические числа форматов изображений
            if len(data) > 4:
                # JPEG: FF D8 FF
                if data[:3] == b'\xff\xd8\xff':
                    return True
                # PNG: 89 50 4E 47
                if data[:4] == b'\x89PNG':
                    return True
                # GIF: GIF87a или GIF89a
                if data[:6] in [b'GIF87a', b'GIF89a']:
                    return True
                # BMP: BM
                if data[:2] == b'BM':
                    return True
            return False
        except:
            return False

    def clear_treeview(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for col in self.tree['columns']:
            self.tree.heading(col, text="")
            self.tree.column(col, width=0)
        self.image_references.clear()

    def build_query(self, sort_column=None, sort_order="ASC"):
        if not self.current_table:
            return "", []

        escaped_current_table = self.escape_table_name(self.current_table)
        used_columns = set()
        select_columns = []

        def add_columns(table_name):
            try:
                cursor = self.connection.cursor()
                cursor.execute(f"PRAGMA table_info({self.escape_table_name(table_name)})")
                columns = cursor.fetchall()
                for col in columns:
                    col_name = col[1]
                    if col_name not in used_columns:
                        select_columns.append(
                            f"{self.escape_table_name(table_name)}.{self.escape_table_name(col_name)}")
                        used_columns.add(col_name)
            except sqlite3.Error:
                pass

        add_columns(self.current_table)
        for join_info in self.joined_tables:
            add_columns(join_info['table2'])

        if self.selected_attributes:
            final_columns = []
            used_columns.clear()
            for attr in self.selected_attributes:
                if '.' in attr:
                    table, col = attr.split('.')
                    if col not in used_columns:
                        final_columns.append(f"{self.escape_table_name(table)}.{self.escape_table_name(col)}")
                        used_columns.add(col)
                else:
                    if attr not in used_columns:
                        final_columns.append(self.escape_table_name(attr))
                        used_columns.add(attr)
            select_columns = final_columns

        if not select_columns:
            return "", []

        select_stmt = "SELECT " + ", ".join(select_columns)
        from_stmt = f"FROM {escaped_current_table}"

        join_stmts = []
        for join_info in self.joined_tables:
            join_type = join_info.get('join_type', 'INNER')
            table2 = self.escape_table_name(join_info['table2'])
            condition = join_info['condition']
            join_stmts.append(f"{join_type} JOIN {table2} ON {condition}")

        order_stmt = ""
        if sort_column:
            sql_order = "DESC" if sort_order == "По убыванию" else "ASC"
            order_stmt = f"ORDER BY {self.escape_table_name(sort_column)} {sql_order}"

        query = f"{select_stmt} {from_stmt} {' '.join(join_stmts)} {order_stmt}"

        display_columns = []
        for col in select_columns:
            clean_col = col.replace('"', '')
            if '.' in clean_col:
                display_columns.append(clean_col.split('.')[-1])
            else:
                display_columns.append(clean_col)

        return query.strip(), display_columns

    def create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0, bg='white', bd=1)
        self.context_menu.add_command(label="📋 Копировать значение", command=self.copy_cell_value)
        self.context_menu.add_command(label="📑 Копировать строку", command=self.copy_row)
        self.context_menu.add_command(label="🏷️ Копировать заголовок", command=self.copy_header)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="✏️ Редактировать значение", command=self.edit_cell_value)
        self.context_menu.add_command(label="🖼️ Добавить/изменить фото", command=self.add_photo_to_selected)
        self.context_menu.add_command(label="👁️ Просмотреть фото", command=self.view_selected_image_full)
        self.context_menu.add_command(label="📸 Экспорт всех фото", command=self.export_all_photos)

        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Double-1>", self.on_double_click)

    def add_photo_to_selected(self):
        """Добавить фото в выбранную ячейку"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите ячейку для добавления фото!")
            return

        item = selection[0]
        column = self.tree.identify_column(self.tree.winfo_pointerx() - self.tree.winfo_rootx())

        if not column or column == '#0':
            return

        col_index = int(column.replace('#', '')) - 1
        column_name = self.tree['columns'][col_index]

        if not self.is_image_column(column_name):
            messagebox.showwarning("Предупреждение", "Выбранная колонка не предназначена для фото!")
            return

        table_name = self.get_column_table(column_name)
        if table_name:
            self.add_photo_dialog(column_name, table_name, item, col_index)

    def edit_cell_value(self):
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        column = self.tree.identify_column(self.tree.winfo_pointerx() - self.tree.winfo_rootx())

        if not column or column == '#0':
            return

        col_index = int(column.replace('#', '')) - 1
        values = list(self.tree.item(item, 'values'))

        if col_index >= len(values):
            return

        current_value = values[col_index]
        column_name = self.tree['columns'][col_index]

        table_name = self.get_column_table(column_name)

        if not table_name:
            messagebox.showwarning("Ошибка", f"Не удалось определить таблицу для колонки '{column_name}'")
            return

        col_type = self.get_column_type(table_name, column_name)

        if col_type and col_type.upper() == 'BLOB':
            self.add_photo_dialog(column_name, table_name, item, col_index)
        elif col_type and col_type.upper() == 'BOOLEAN':
            dialog = ModernBooleanEditDialog(self.root, column_name, current_value)
            self.root.wait_window(dialog.top)
            new_value = dialog.result
            if new_value is not None:
                self.update_cell_value(item, col_index, new_value, column_name, table_name)
        else:
            new_value = simpledialog.askstring("Редактирование",
                                               f"Новое значение для '{column_name}':",
                                               initialvalue=str(current_value) if current_value is not None else "")
            if new_value is not None:
                self.update_cell_value(item, col_index, new_value, column_name, table_name)

    def update_image_value(self, item, col_index, image_data, column_name, table_name):
        """Обновление значения изображения в базе данных"""
        try:
            cursor = self.connection.cursor()

            primary_key_value = self.find_primary_key_value(item, table_name)

            if not primary_key_value:
                messagebox.showerror("Ошибка", "Не удалось определить первичный ключ для обновления!")
                return

            cursor.execute(f"PRAGMA table_info({self.escape_table_name(table_name)})")
            columns_info = cursor.fetchall()
            primary_key = columns_info[0][1]

            query = f"UPDATE {self.escape_table_name(table_name)} SET {self.escape_table_name(column_name)} = ? WHERE {primary_key} = ?"
            cursor.execute(query, (image_data, primary_key_value))
            self.connection.commit()

            self.display_table_data()
            self.update_status("✅ Фото обновлено!")

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка обновления фото: {e}")

    def view_selected_image(self):
        """Просмотр выбранного изображения"""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        column = self.tree.identify_column(self.tree.winfo_pointerx() - self.tree.winfo_rootx())

        if not column or column == '#0':
            return

        col_index = int(column.replace('#', '')) - 1
        column_name = self.tree['columns'][col_index]

        if not self.is_image_column(column_name):
            messagebox.showwarning("Предупреждение", "Выбранная колонка не содержит фото!")
            return

        try:
            # Получаем значение из Treeview
            values = self.tree.item(item, 'values')
            if col_index >= len(values):
                return

            cell_value = values[col_index]

            # Если в ячейке текст "🖼️ Фото", значит нужно получить реальные данные из БД
            if cell_value == "🖼️ Фото":
                # Находим первичный ключ записи
                cursor = self.connection.cursor()

                # Получаем первичный ключ таблицы
                cursor.execute(f"PRAGMA table_info({self.escape_table_name(self.current_table)})")
                columns_info = cursor.fetchall()
                primary_key_name = columns_info[0][1]

                # Находим значение первичного ключа в отображаемых данных
                pk_index = -1
                for i, col in enumerate(self.tree['columns']):
                    if col == primary_key_name:
                        pk_index = i
                        break

                if pk_index != -1 and pk_index < len(values):
                    primary_key_value = values[pk_index]

                    # Получаем данные фото из БД
                    query = f"SELECT {self.escape_table_name(column_name)} FROM {self.escape_table_name(self.current_table)} WHERE {primary_key_name} = ?"
                    cursor.execute(query, (primary_key_value,))
                    result = cursor.fetchone()

                    if result and result[0] and isinstance(result[0], bytes):
                        image_data = result[0]
                        self.view_image(column_name, image_data)
                    else:
                        messagebox.showwarning("Предупреждение", "Фото не найдено в базе данных!")
                else:
                    messagebox.showwarning("Предупреждение", "Не удалось определить запись!")
            else:
                messagebox.showinfo("Информация", "В этой ячейке нет фото")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка просмотра фото: {str(e)}")

    def view_image(self, column_name, image_data, record_info=""):
        """Просмотр полноразмерного изображения"""
        try:
            image_window = tk.Toplevel(self.root)
            image_window.title(f"Фото - {column_name} {record_info}")
            image_window.geometry("800x600")

            # Создаем главный фрейм
            main_frame = ttk.Frame(image_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Загружаем изображение
            image = Image.open(io.BytesIO(image_data))

            # Получаем оригинальный размер
            original_width, original_height = image.size

            # Рассчитываем размер для отображения
            max_width = 750
            max_height = 500

            if original_width > max_width or original_height > max_height:
                ratio = min(max_width / original_width, max_height / original_height)
                new_size = (int(original_width * ratio), int(original_height * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            # Преобразуем для Tkinter
            photo = ImageTk.PhotoImage(image)

            # Создаем метку с изображением
            label = tk.Label(main_frame, image=photo)
            label.image = photo
            label.pack(expand=True)

            # Панель информации
            info_frame = ttk.Frame(main_frame)
            info_frame.pack(fill=tk.X, pady=10)

            ttk.Label(info_frame,
                      text=f"Размер: {original_width}x{original_height} пикселей | "
                           f"Объем: {len(image_data)} байт").pack(side=tk.LEFT)

            # Панель кнопок
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=10)

            ttk.Button(button_frame, text="💾 Сохранить фото",
                       command=lambda: self.save_image(image_data, f"photo_{column_name}_{record_info}"),
                       style='Primary.TButton').pack(side=tk.LEFT, padx=5)

            ttk.Button(button_frame, text="🖨️ Печать",
                       command=lambda: self.print_image(Image.open(io.BytesIO(image_data)),
                                                        f"{column_name}_{record_info}"),
                       style='Secondary.TButton').pack(side=tk.LEFT, padx=5)

            ttk.Button(button_frame, text="✏️ Редактировать",
                       command=lambda: self.edit_image_dialog(column_name, image_data, image_window),
                       style='Success.TButton').pack(side=tk.LEFT, padx=5)

            ttk.Button(button_frame, text="❌ Закрыть",
                       command=image_window.destroy,
                       style='Danger.TButton').pack(side=tk.RIGHT)

            # Добавляем возможность изменения размера окна
            image_window.resizable(True, True)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка просмотра фото: {e}")

    def view_image_with_info(self, column_name, image_data, primary_key=None, record_id=None):
        """Просмотр изображения с информацией о записи"""
        record_info = f"(ID: {record_id})" if record_id else ""
        self.view_image(column_name, image_data, record_info)

    def save_image(self, image_data):
        """Сохранение изображения в файл"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
        )

        if file_path:
            try:
                with open(file_path, 'wb') as f:
                    f.write(image_data)
                self.update_status(f"✅ Фото сохранено: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка сохранения: {e}")

    def copy_cell_value(self):
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            column = self.tree.identify_column(self.tree.winfo_pointerx() - self.tree.winfo_rootx())
            if column:
                col_index = int(column.replace('#', '')) - 1
                values = self.tree.item(item, 'values')
                if values and col_index < len(values):
                    value = str(values[col_index])
                    self.root.clipboard_clear()
                    self.root.clipboard_append(value)
                    self.update_status("✅ Значение скопировано в буфер")

    def copy_row(self):
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            values = self.tree.item(item, 'values')
            if values:
                row_text = "\t".join(str(v) for v in values)
                self.root.clipboard_clear()
                self.root.clipboard_append(row_text)
                self.update_status("✅ Строка скопирована в буфер")

    def copy_header(self):
        column = self.tree.identify_column(self.tree.winfo_pointerx() - self.tree.winfo_rootx())
        if column:
            col_index = int(column.replace('#', '')) - 1
            columns = self.tree['columns']
            if col_index < len(columns):
                header = columns[col_index]
                self.root.clipboard_clear()
                self.root.clipboard_append(header)
                self.update_status("✅ Заголовок скопирован в буфер")

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if item and column != '#0':
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if item and column != '#0':
            self.tree.selection_set(item)
            self.edit_cell_value()

    def get_column_table(self, column_name):
        """Определяет, к какой таблице принадлежит колонка"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({self.escape_table_name(self.current_table)})")
            columns = cursor.fetchall()
            for col in columns:
                if col[1] == column_name:
                    return self.current_table
        except sqlite3.Error:
            pass

        for join_info in self.joined_tables:
            table_name = join_info['table2']
            try:
                cursor = self.connection.cursor()
                cursor.execute(f"PRAGMA table_info({self.escape_table_name(table_name)})")
                columns = cursor.fetchall()
                for col in columns:
                    if col[1] == column_name:
                        return table_name
            except sqlite3.Error:
                continue

        return None

    def get_column_type(self, table_name, column_name):
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({self.escape_table_name(table_name)})")
            columns = cursor.fetchall()
            for col in columns:
                if col[1] == column_name:
                    return col[2]
        except sqlite3.Error:
            pass
        return None

    def update_cell_value(self, item, col_index, new_value, column_name, table_name):
        if not table_name:
            return

        try:
            values = list(self.tree.item(item, 'values'))
            old_value = values[col_index]
            values[col_index] = new_value

            cursor = self.connection.cursor()

            cursor.execute(f"PRAGMA table_info({self.escape_table_name(table_name)})")
            columns_info = cursor.fetchall()
            column_names = [col[1] for col in columns_info]

            primary_key_value = self.find_primary_key_value(item, table_name)

            if not primary_key_value:
                messagebox.showerror("Ошибка", "Не удалось определить первичный ключ для обновления!")
                return

            processed_value = new_value
            col_type = self.get_column_type(table_name, column_name)
            if col_type and col_type.upper() == 'BOOLEAN':
                if new_value.lower() in ['true', '1', 'да', 'yes']:
                    processed_value = 1
                elif new_value.lower() in ['false', '0', 'нет', 'no']:
                    processed_value = 0
                else:
                    processed_value = None

            primary_key = column_names[0]

            set_clause = f"{self.escape_table_name(column_name)} = ?"
            query = f"UPDATE {self.escape_table_name(table_name)} SET {set_clause} WHERE {primary_key} = ?"

            cursor.execute(query, (processed_value, primary_key_value))
            self.connection.commit()

            self.tree.item(item, values=values)
            self.update_status(f"✅ Значение в таблице '{table_name}' обновлено!")

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка обновления значения: {e}")

    def find_primary_key_value(self, item, table_name):
        """Находит значение первичного ключа для указанной таблицы в отображаемых данных"""
        try:
            values = self.tree.item(item, 'values')
            display_columns = self.tree['columns']

            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({self.escape_table_name(table_name)})")
            columns_info = cursor.fetchall()

            primary_key_name = columns_info[0][1]

            for i, col_name in enumerate(display_columns):
                if col_name == primary_key_name:
                    return values[i] if i < len(values) else None

            return None

        except sqlite3.Error:
            return None

    def delete_record(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите запись для удаления!")
            return

        if not messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить выбранную запись?"):
            return

        item = selection[0]
        values = self.tree.item(item, 'values')

        if not values:
            return

        try:
            cursor = self.connection.cursor()

            cursor.execute(f"PRAGMA table_info({self.escape_table_name(self.current_table)})")
            columns_info = cursor.fetchall()

            primary_key = columns_info[0][1]
            primary_key_value = values[0]

            query = f"DELETE FROM {self.escape_table_name(self.current_table)} WHERE {primary_key} = ?"
            cursor.execute(query, (primary_key_value,))
            self.connection.commit()

            self.tree.delete(item)
            self.update_status("✅ Запись удалена!")

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка удаления записи: {e}")

    def rename_attribute_dialog(self):
        if not self.current_table:
            messagebox.showwarning("Предупреждение", "Сначала выберите таблицу!")
            return

        try:
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({self.escape_table_name(self.current_table)})")
            columns = cursor.fetchall()

            if not columns:
                messagebox.showwarning("Предупреждение", "В таблице нет атрибутов!")
                return

            old_name = simpledialog.askstring("Переименование атрибута",
                                              "Выберите атрибут для переименования:",
                                              initialvalue=columns[0][1])
            if not old_name:
                return

            column_names = [col[1] for col in columns]
            if old_name not in column_names:
                messagebox.showerror("Ошибка", f"Атрибут '{old_name}' не найден!")
                return

            new_name = simpledialog.askstring("Переименование атрибута",
                                              f"Новое имя для атрибута '{old_name}':",
                                              initialvalue=old_name)
            if not new_name:
                return

            if new_name == old_name:
                return

            self.rename_attribute(old_name, new_name)

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка получения структуры таблицы: {e}")

    def rename_attribute(self, old_name, new_name):
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({self.escape_table_name(self.current_table)})")
            columns_info = cursor.fetchall()

            new_columns = []
            for col in columns_info:
                if col[1] == old_name:
                    new_columns.append(f'"{new_name}" {col[2]}')
                else:
                    new_columns.append(f'"{col[1]}" {col[2]}')

            temp_table = f"temp_{self.current_table}"
            create_query = f"CREATE TABLE {self.escape_table_name(temp_table)} ({', '.join(new_columns)})"
            cursor.execute(create_query)

            column_names = [f'"{col[1]}"' for col in columns_info]
            insert_query = f"INSERT INTO {self.escape_table_name(temp_table)} SELECT {', '.join(column_names)} FROM {self.escape_table_name(self.current_table)}"
            cursor.execute(insert_query)

            cursor.execute(f"DROP TABLE {self.escape_table_name(self.current_table)}")
            cursor.execute(
                f"ALTER TABLE {self.escape_table_name(temp_table)} RENAME TO {self.escape_table_name(self.current_table)}")

            self.connection.commit()
            self.display_table_data()
            self.update_status(f"✅ Атрибут '{old_name}' переименован в '{new_name}'!")

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка переименования атрибута: {e}")

    def add_column_dialog(self):
        if not self.current_table:
            messagebox.showwarning("Предупреждение", "Сначала выберите таблицу!")
            return

        dialog = ModernAddColumnDialog(self.root, self)
        self.root.wait_window(dialog.top)

    def add_column_to_table(self, column_name, column_type, default_value=None):
        try:
            cursor = self.connection.cursor()
            query = f"ALTER TABLE {self.escape_table_name(self.current_table)} ADD COLUMN {self.escape_table_name(column_name)} {column_type}"

            if default_value is not None:
                if column_type.upper() == 'BOOLEAN':
                    if default_value.lower() in ['true', '1', 'да', 'yes']:
                        default_value = '1'
                    else:
                        default_value = '0'
                query += f" DEFAULT {default_value}"

            cursor.execute(query)
            self.connection.commit()

            if default_value is not None:
                update_query = f"UPDATE {self.escape_table_name(self.current_table)} SET {self.escape_table_name(column_name)} = ?"
                cursor.execute(update_query, (default_value,))
                self.connection.commit()

            self.update_status(f"✅ Колонка '{column_name}' добавлена в таблицу '{self.current_table}'!")
            self.display_table_data()

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка добавления колонки: {e}")

    def get_available_columns(self):
        columns_set = set()

        if self.current_table:
            try:
                cursor = self.connection.cursor()
                cursor.execute(f"PRAGMA table_info({self.escape_table_name(self.current_table)})")
                table_columns = cursor.fetchall()
                for col in table_columns:
                    columns_set.add(col[1])
            except sqlite3.Error:
                pass

        for join_info in self.joined_tables:
            table_name = join_info['table2']
            try:
                cursor = self.connection.cursor()
                cursor.execute(f"PRAGMA table_info({self.escape_table_name(table_name)})")
                table_columns = cursor.fetchall()
                for col in table_columns:
                    col_name = col[1]
                    if col_name not in columns_set:
                        columns_set.add(col_name)
            except sqlite3.Error:
                pass

        return sorted(list(columns_set))

    def get_all_tables_columns(self):
        all_columns = {}
        used_columns = set()

        if self.current_table:
            try:
                cursor = self.connection.cursor()
                cursor.execute(f"PRAGMA table_info({self.escape_table_name(self.current_table)})")
                columns = cursor.fetchall()
                table_columns = []
                for col in columns:
                    if col[1] not in used_columns:
                        table_columns.append(col[1])
                        used_columns.add(col[1])
                all_columns[self.current_table] = table_columns
            except sqlite3.Error:
                pass

        for join_info in self.joined_tables:
            table_name = join_info['table2']
            try:
                cursor = self.connection.cursor()
                cursor.execute(f"PRAGMA table_info({self.escape_table_name(table_name)})")
                columns = cursor.fetchall()
                table_columns = []
                for col in columns:
                    if col[1] not in used_columns:
                        table_columns.append(col[1])
                        used_columns.add(col[1])
                all_columns[table_name] = table_columns
            except sqlite3.Error:
                pass

        return all_columns

    def set_selected_attributes(self, attributes):
        self.selected_attributes = attributes
        self.update_attributes_label()
        self.display_table_data()

    def update_attributes_label(self):
        if self.selected_attributes:
            attrs_text = ", ".join([attr.split('.')[-1] for attr in self.selected_attributes[:3]])
            if len(self.selected_attributes) > 3:
                attrs_text += f"... (+{len(self.selected_attributes) - 3})"
            self.attributes_label.config(text=f"👁️ Отображаемые атрибуты: {attrs_text}")
        else:
            self.attributes_label.config(text="👁️ Отображаемые атрибуты: все")

    def apply_sorting(self):
        if (self.current_table or self.joined_tables) and self.sort_column.get():
            sort_order = self.sort_order.get()
            self.display_table_data(self.sort_column.get(), sort_order)

    def refresh_data(self):
        if self.current_table or self.joined_tables:
            self.display_table_data()
        self.update_table_list()
        self.update_db_label()
        self.update_status("✅ Данные обновлены")

    def quick_join_tables(self):
        if not self.current_table:
            messagebox.showwarning("Предупреждение", "Сначала выберите основную таблицу!")
            return

        tables = []
        for i in range(self.table_listbox.size()):
            table = self.table_listbox.get(i)
            if table != self.current_table:
                tables.append(table)

        if not tables:
            messagebox.showinfo("Информация", "Нет других таблиц для соединения!")
            return

        dialog = ModernMultiTableSelectDialog(self.root, self, tables)
        self.root.wait_window(dialog.top)

        if dialog.selected_tables:
            for table2 in dialog.selected_tables:
                common_columns = self.find_common_columns(self.current_table, table2)

                if not common_columns:
                    messagebox.showwarning("Предупреждение",
                                           f"Не найдено общих полей между '{self.current_table}' и '{table2}'!")
                    continue

                join_column = common_columns[0]

                if self.join_tables(table2, join_column, join_column, "INNER"):
                    self.update_status(
                        f"✅ Автоматическое соединение: {self.current_table}.{join_column} = {table2}.{join_column}")

    def find_common_columns(self, table1, table2):
        try:
            cursor = self.connection.cursor()

            cursor.execute(f"PRAGMA table_info({self.escape_table_name(table1)})")
            table1_columns = [col[1] for col in cursor.fetchall()]

            cursor.execute(f"PRAGMA table_info({self.escape_table_name(table2)})")
            table2_columns = [col[1] for col in cursor.fetchall()]

            common_columns = list(set(table1_columns) & set(table2_columns))
            return common_columns

        except sqlite3.Error:
            return []

    def join_tables(self, table2, table1_attr, table2_attr, join_type="INNER"):
        try:
            cursor = self.connection.cursor()

            cursor.execute(f"PRAGMA table_info({self.escape_table_name(self.current_table)})")
            table1_columns = [col[1] for col in cursor.fetchall()]
            if table1_attr not in table1_columns:
                messagebox.showerror("Ошибка", f"Атрибут '{table1_attr}' не найден!")
                return False

            cursor.execute(f"PRAGMA table_info({self.escape_table_name(table2)})")
            table2_columns = [col[1] for col in cursor.fetchall()]
            if table2_attr not in table2_columns:
                messagebox.showerror("Ошибка", f"Атрибут '{table2_attr}' не найден!")
                return False

            for join_info in self.joined_tables:
                if join_info['table2'] == table2:
                    messagebox.showwarning("Предупреждение", f"Таблица '{table2}' уже соединена!")
                    return False

            condition = f"{self.escape_table_name(self.current_table)}.{self.escape_table_name(table1_attr)} = {self.escape_table_name(table2)}.{self.escape_table_name(table2_attr)}"

            join_info = {'table2': table2, 'condition': condition, 'join_type': join_type}
            self.joined_tables.append(join_info)
            self.table_joins[self.current_table] = self.joined_tables.copy()

            self.update_join_info()
            self.display_table_data()
            self.update_status(f"✅ Таблицы соединены: {self.current_table} ↔ {table2}")
            return True

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка соединения таблиц: {e}")
            return False

    def update_join_info(self):
        self.join_info_text.delete(1.0, tk.END)
        if self.joined_tables:
            self.join_info_text.insert(tk.END, f"Основная: {self.current_table}\n\n")
            for i, join_info in enumerate(self.joined_tables):
                self.join_info_text.insert(tk.END, f"{i + 1}. {join_info['table2']}\n")
                self.join_info_text.insert(tk.END, f"   Условие: {join_info['condition']}\n")
                self.join_info_text.insert(tk.END, f"   Тип: {join_info['join_type']}\n\n")
        else:
            self.join_info_text.insert(tk.END, "Нет активных соединений")

    def remove_join(self):
        if not self.joined_tables:
            return

        if self.joined_tables:
            removed_join = self.joined_tables.pop()
            self.table_joins[self.current_table] = self.joined_tables.copy()
            self.update_join_info()
            self.display_table_data()
            self.update_status(f"✅ Соединение с '{removed_join['table2']}' удалено")

    def clear_joins(self):
        self.joined_tables.clear()
        if self.current_table:
            self.table_joins[self.current_table] = []
        self.update_join_info()
        if self.current_table:
            self.display_table_data()
        self.update_status("✅ Все соединения очищены")

    def print_data(self):
        """Печать данных в PDF с поддержкой кириллицы"""
        if not self.current_table and not self.joined_tables:
            messagebox.showwarning("Предупреждение", "Нет данных для печати!")
            return

        file_path = filedialog.asksaveasfilename(
            title="Сохранить PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            # Получаем данные
            query, display_columns = self.build_query()
            cursor = self.connection.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()

            # Создаем PDF
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            # Регистрируем шрифт Arial (если есть)
            font_name = "Helvetica"  # По умолчанию

            try:
                # Попробуем найти Arial в системных путях
                possible_font_paths = [
                    "C:/Windows/Fonts/arial.ttf",
                    "C:/Windows/Fonts/arialbd.ttf",
                    "/usr/share/fonts/truetype/msttcorefonts/arial.ttf",
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
                ]

                for font_path in possible_font_paths:
                    if os.path.exists(font_path):
                        pdfmetrics.registerFont(TTFont('Arial', font_path))
                        font_name = 'Arial'
                        break
            except:
                pass  # Используем Helvetica по умолчанию

            pdf = canvas.Canvas(file_path, pagesize=landscape(A4))
            pdf.setTitle(f"База данных - {self.current_table}")

            # Настройка шрифта
            pdf.setFont(font_name, 12)

            # Заголовок
            title = f"Таблица: {self.current_table}"
            pdf.setFont(font_name, 16)  # Только обычный шрифт, не жирный
            pdf.drawString(50, 550, title)

            pdf.setFont(font_name, 10)
            pdf.drawString(50, 530, f"База данных: {os.path.basename(self.db_name)}")
            pdf.drawString(50, 515, f"Дата экспорта: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")

            # Настройки таблицы
            col_width = 80
            row_height = 20
            start_x = 50
            start_y = 490

            # Заголовки колонок
            pdf.setFont(font_name, 8)  # Только обычный шрифт
            for i, col in enumerate(display_columns):
                x = start_x + i * col_width
                pdf.rect(x, start_y, col_width, row_height)
                # Используем безопасный текст
                safe_text = self.safe_text(str(col)[:15])
                pdf.drawString(x + 2, start_y + 5, safe_text)

            # Данные
            pdf.setFont(font_name, 7)
            y_pos = start_y - row_height

            for row in rows:
                if y_pos < 50:  # Новая страница
                    pdf.showPage()
                    y_pos = 750
                    # Повторяем заголовки на новой странице
                    pdf.setFont(font_name, 8)
                    for i, col in enumerate(display_columns):
                        x = start_x + i * col_width
                        pdf.rect(x, y_pos + row_height, col_width, row_height)
                        safe_text = self.safe_text_for_pdf(str(col)[:15])
                        pdf.drawString(x + 2, y_pos + row_height + 5, safe_text)
                    y_pos = y_pos - row_height
                    pdf.setFont(font_name, 7)

                for i, value in enumerate(row):
                    x = start_x + i * col_width
                    pdf.rect(x, y_pos, col_width, row_height)

                    # Форматируем значение для отображения
                    display_value = self.format_value_for_pdf(value)
                    safe_text = self.safe_text(display_value)

                    pdf.drawString(x + 2, y_pos + 5, safe_text)

                y_pos -= row_height

            pdf.save()
            messagebox.showinfo("Успех", f"PDF успешно создан:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка создания PDF: {e}")

    def safe_text(self, text):
        """Обеспечивает безопасное отображение текста в PDF"""
        # Заменяем проблемные символы
        replacements = {
            '�': '',
            '̀': '',
            '́': '',
            '̂': '',
            '̃': '',
            '̄': '',
            '̅': '',
            '̆': '',
            '̇': '',
            '̈': '',
            '̉': '',
            '̊': '',
            '̋': '',
            '̌': '',
            '̍': '',
            '̎': '',
            '̏': '',
            '̐': '',
            '̑': '',
            '̒': '',
            '̓': '',
            '̔': '',
            '̕': '',
            '̖': '',
            '̗': '',
            '̘': '',
            '̙': '',
            '̚': '',
            '̛': '',
            '̜': '',
            '̝': '',
            '̞': '',
            '̟': '',
            '̠': '',
            '̡': '',
            '̢': '',
            '̣': '',
            '̤': '',
            '̥': '',
            '̦': '',
            '̧': '',
            '̨': '',
            '̩': '',
            '̪': '',
            '̫': '',
            '̬': '',
            '̭': '',
            '̮': '',
            '̯': '',
            '̰': '',
            '̱': '',
            '̲': '',
            '̳': '',
            '̴': '',
            '̵': '',
            '̶': '',
            '̷': '',
            '̸': '',
            '̹': '',
            '̺': '',
            '̻': '',
            '̼': '',
            '̽': '',
            '̾': '',
            '̿': '',
            '̀': '',
            '́': '',
            '͂': '',
            '̓': '',
            '̈́': '',
            'ͅ': '',
            '͆': '',
            '͇': '',
            '͈': '',
            '͉': '',
            '͊': '',
            '͋': '',
            '͌': '',
            '͍': '',
            '͎': '',
            '͏': '',
            '͐': '',
            '͑': '',
            '͒': '',
            '͓': '',
            '͔': '',
            '͕': '',
            '͖': '',
            '͗': '',
            '͘': '',
            '͙': '',
            '͚': '',
            '͛': '',
            '͜': '',
            '͝': '',
            '͞': '',
            '͟': '',
            '͠': '',
            '͡': ''
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text[:20]  # Ограничиваем длину

    def format_value_for_pdf(self, value):
        """Форматирует значение для PDF"""
        if value is None:
            return ""
        elif isinstance(value, bytes):
            return "🖼️"
        elif isinstance(value, bool):
            return "Да" if value else "Нет"
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            text = str(value)
            return text[:17] + "..." if len(text) > 20 else text

    def import_excel(self):
        if not self.current_table:
            messagebox.showwarning("Предупреждение", "Сначала выберите таблицу!")
            return

        file_path = filedialog.askopenfilename(
            title="Выберите Excel файл",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            df = pd.read_excel(file_path)

            if df.empty:
                messagebox.showwarning("Предупреждение", "Файл Excel пуст!")
                return

            dialog = ModernExcelImportDialog(self.root, self, df.columns.tolist())
            self.root.wait_window(dialog.top)

            if not dialog.proceed:
                return

            cursor = self.connection.cursor()

            cursor.execute(f"PRAGMA table_info({self.escape_table_name(self.current_table)})")
            table_columns = [col[1] for col in cursor.fetchall()]

            for _, row in df.iterrows():
                values = []
                for table_col in table_columns:
                    if table_col in df.columns:
                        value = row[table_col]
                        if pd.isna(value):
                            values.append(None)
                        else:
                            values.append(value)
                    else:
                        values.append(None)

                placeholders = ", ".join(["?" for _ in table_columns])
                query = f"INSERT INTO {self.escape_table_name(self.current_table)} VALUES ({placeholders})"
                cursor.execute(query, values)

            self.connection.commit()
            self.display_table_data()
            self.update_status(f"✅ Данные импортированы из {os.path.basename(file_path)}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка импорта Excel: {e}")

    def export_excel(self):
        """Экспорт в Excel (базовый)"""
        if not self.current_table and not self.joined_tables:
            messagebox.showwarning("Предупреждение", "Нет данных для экспорта!")
            return

        # Используем домашнюю папку пользователя по умолчанию
        initial_dir = os.path.expanduser("~")

        file_path = filedialog.asksaveasfilename(
            title="Сохранить как Excel (базовый)",
            defaultextension=".xlsx",
            initialdir=initial_dir,
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            query, display_columns = self.build_query()
            cursor = self.connection.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()

            df = pd.DataFrame(rows, columns=display_columns)

            for i, col in enumerate(display_columns):
                if self.is_image_column(col):
                    df[col] = ["🖼️ Фото" if isinstance(val, bytes) and self.is_valid_image_blob(val) else val for val in
                               df[col]]

            # Создаем директорию, если она не существует
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

            df.to_excel(file_path, index=False, engine='openpyxl')

            self.update_status(f"✅ Данные экспортированы в {os.path.basename(file_path)}")
            messagebox.showinfo("Успех", f"Данные успешно экспортированы в:\n{file_path}")

        except PermissionError as e:
            messagebox.showerror("Ошибка доступа",
                                 f"Нет прав доступа к файлу:\n{file_path}\n\n"
                                 f"Сохраните файл в другую папку (например, Документы или Рабочий стол)")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка экспорта в Excel: {e}")

    def escape_table_name(self, table_name):
        return f'"{table_name}"'

    def update_db_label(self):
        if self.db_name:
            db_name = os.path.basename(self.db_name)
            self.db_label.config(text=f"📁 База данных: {db_name}")

    def create_table_dialog(self):
        dialog = ModernCreateTableDialog(self.root, self)
        self.root.wait_window(dialog.top)

    def create_table(self, table_name, columns):
        try:
            cursor = self.connection.cursor()
            columns_sql = []
            for col in columns:
                col_name = f'"{col["name"]}"'
                columns_sql.append(f"{col_name} {col['type']}")

            query = f"CREATE TABLE IF NOT EXISTS {self.escape_table_name(table_name)} ({', '.join(columns_sql)})"
            cursor.execute(query)
            self.connection.commit()

            self.update_status(f"✅ Таблица '{table_name}' создана успешно!")
            self.update_table_list()

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка создания таблицы: {e}")

    def add_record_dialog(self):
        if not self.current_table:
            messagebox.showwarning("Предупреждение", "Выберите таблицу!")
            return

        dialog = ModernAddRecordDialog(self.root, self)
        self.root.wait_window(dialog.top)

    def add_record(self, values):
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({self.escape_table_name(self.current_table)})")
            columns_info = cursor.fetchall()
            columns = [column[1] for column in columns_info]
            columns_types = [column[2] for column in columns_info]

            processed_values = []
            for i, value in enumerate(values):
                col_type = columns_types[i].upper()

                if value is None or value == "":
                    processed_values.append(None)
                elif col_type == 'BOOLEAN':
                    if isinstance(value, str):
                        value_lower = value.lower().strip()
                        if value_lower in ['true', '1', 'да', 'yes', 'истина']:
                            processed_values.append(1)
                        elif value_lower in ['false', '0', 'нет', 'no', 'ложь']:
                            processed_values.append(0)
                        else:
                            processed_values.append(None)
                    else:
                        processed_values.append(1 if value else 0)
                else:
                    processed_values.append(value)

            placeholders = ", ".join(["?" for _ in columns])
            query = f"INSERT INTO {self.escape_table_name(self.current_table)} VALUES ({placeholders})"

            cursor.execute(query, processed_values)
            self.connection.commit()

            self.update_status("✅ Запись добавлена успешно!")
            self.display_table_data()

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка добавления записи: {e}")

    def join_tables_dialog(self):
        if not self.current_table:
            messagebox.showwarning("Предупреждение", "Сначала выберите основную таблицу!")
            return

        dialog = ModernJoinTablesDialog(self.root, self)
        self.root.wait_window(dialog.top)

    def select_attributes_dialog(self):
        if not self.current_table and not self.joined_tables:
            messagebox.showwarning("Предупреждение", "Сначала выберите таблицу!")
            return

        dialog = ModernSelectAttributesDialog(self.root, self)
        self.root.wait_window(dialog.top)

    def check_and_display_photos(self):
        """Быстрая проверка наличия фото в таблице"""
        if not self.current_table:
            return

        try:
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({self.escape_table_name(self.current_table)})")
            columns = cursor.fetchall()

            image_columns = []
            for col in columns:
                if col[2].upper() == 'BLOB':
                    image_columns.append(col[1])

            if image_columns:
                photo_found = False
                for col_name in image_columns:
                    # Проверяем первую запись
                    cursor.execute(f"SELECT COUNT(*) FROM {self.current_table} WHERE {col_name} IS NOT NULL")
                    result = cursor.fetchone()

                    if result and result[0] > 0:
                        self.update_status(f"✅ Найдено {result[0]} фото в колонке '{col_name}'")
                        photo_found = True

                if not photo_found:
                    self.update_status("ℹ️ В таблице есть колонки для фото, но фото не найдены")

        except Exception as e:
            pass

    def inspect_database(self):
        """Функция для изучения структуры базы данных"""
        try:
            if not self.connection:
                messagebox.showwarning("Предупреждение", "База данных не подключена!")
                return

            cursor = self.connection.cursor()

            # Показать все таблицы
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()

            result_text = "🔍 ИССЛЕДОВАНИЕ БАЗЫ ДАННЫХ\n"
            result_text += "=" * 50 + "\n\n"
            result_text += f"📁 База данных: {os.path.basename(self.db_name)}\n"
            result_text += f"📋 Найдено таблиц: {len(tables)}\n\n"

            for table in tables:
                table_name = table[0]
                result_text += f"📊 ТАБЛИЦА: {table_name}\n"
                result_text += "-" * 30 + "\n"

                # Показать структуру таблицы
                cursor.execute(f"PRAGMA table_info({self.escape_table_name(table_name)})")
                columns = cursor.fetchall()
                result_text += "Столбцы:\n"
                for col in columns:
                    result_text += f"  - {col[1]} (тип: {col[2]})\n"

                # Показать количество записей
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {self.escape_table_name(table_name)}")
                    count = cursor.fetchone()[0]
                    result_text += f"📈 Записей: {count}\n"
                except:
                    result_text += "📈 Записей: недоступно\n"

                result_text += "\n"

            # Показать результат в новом окне
            self.show_text_dialog("Исследование базы данных", result_text)

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка исследования базы данных: {e}")

    def find_and_display_all_photos(self):
        """Находит и сохраняет все фотографии из базы данных"""
        try:
            if not self.connection:
                messagebox.showwarning("Предупреждение", "База данных не подключена!")
                return

            cursor = self.connection.cursor()

            tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()

            photo_count = 0
            result_text = "🖼️ ПОИСК ФОТОГРАФИЙ В БАЗЕ ДАННЫХ\n"
            result_text += "=" * 50 + "\n\n"

            for table in tables:
                table_name = table[0]
                result_text += f"📋 Таблица: {table_name}\n"

                cursor.execute(f"PRAGMA table_info({self.escape_table_name(table_name)})")
                columns = cursor.fetchall()

                table_photo_count = 0
                for column in columns:
                    col_name = column[1]
                    col_type = column[2]

                    # Проверяем различные варианты названий столбцов с фото
                    if (col_type.upper() == 'BLOB' or
                            any(photo_keyword in col_name.lower() for photo_keyword in
                                ['photo', 'image', 'img', 'picture', 'pic'])):

                        result_text += f"  🔍 Проверка столбца: {col_name} ({col_type})\n"

                        # Получаем все записи с фотографиями
                        cursor.execute(f"SELECT rowid, {col_name} FROM {table_name} WHERE {col_name} IS NOT NULL")
                        photos = cursor.fetchall()

                        for rowid, photo_data in photos:
                            if isinstance(photo_data, bytes) and len(photo_data) > 100:  # Минимальный размер для фото
                                filename = f"photo_{table_name}_{col_name}_{rowid}.jpg"
                                try:
                                    with open(filename, 'wb') as f:
                                        f.write(photo_data)
                                    result_text += f"    ✅ Сохранено: {filename} ({len(photo_data)} bytes)\n"
                                    photo_count += 1
                                    table_photo_count += 1
                                except Exception as e:
                                    result_text += f"    ❌ Ошибка сохранения: {e}\n"
                            elif isinstance(photo_data, bytes):
                                result_text += f"    ℹ Найдены бинарные данные, но размер слишком мал для фото: {len(photo_data)} bytes\n"

                if table_photo_count == 0:
                    result_text += "  ❌ Фотографии не найдены\n"
                else:
                    result_text += f"  📊 Найдено фотографий: {table_photo_count}\n"

                result_text += "\n"

            if photo_count == 0:
                result_text += "⚠ Фотографии не найдены в базе данных\n"
            else:
                result_text += f"✅ Всего сохранено фотографий: {photo_count}\n"

            # Показать результат
            self.show_text_dialog("Результаты поиска фотографий", result_text)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при поиске фотографий: {e}")

    def show_text_dialog(self, title, text):
        """Показывает текстовый диалог с результатами"""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("800x600")
        dialog.configure(bg='#f5f5f5')

        main_frame = ttk.Frame(dialog, style='Modern.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Текстовое поле с прокруткой
        text_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        text_frame.pack(fill=tk.BOTH, expand=True)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, bg='white', font=('Consolas', 10))
        text_widget.insert(1.0, text)
        text_widget.config(state=tk.DISABLED)

        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Кнопки
        button_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="💾 Сохранить в файл",
                   command=lambda: self.save_text_to_file(text, title),
                   style='Primary.TButton').pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="❌ Закрыть",
                   command=dialog.destroy,
                   style='Secondary.TButton').pack(side=tk.LEFT, padx=5)

    def save_text_to_file(self, text, title):
        """Сохраняет текст в файл"""
        file_path = filedialog.asksaveasfilename(
            title=f"Сохранить {title}",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                self.update_status(f"✅ Файл сохранен: {os.path.basename(file_path)}")
                messagebox.showinfo("Успех", f"Файл успешно сохранен:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка сохранения файла: {e}")

    def display_photo_from_db(self, photo_column, record_id=None):
        """Функция для извлечения и сохранения фотографии из базы данных"""
        try:
            if not self.current_table:
                messagebox.showwarning("Предупреждение", "Сначала выберите таблицу!")
                return

            cursor = self.connection.cursor()

            # Определяем условие для выбора записи
            if record_id is not None:
                # Ищем поле ID
                cursor.execute(f"PRAGMA table_info({self.escape_table_name(self.current_table)})")
                columns = cursor.fetchall()
                id_columns = [col[1] for col in columns if 'id' in col[1].lower()]

                if id_columns:
                    id_column = id_columns[0]
                    condition = f"WHERE {id_column} = ?"
                    params = (record_id,)
                else:
                    condition = "LIMIT 1"
                    params = ()
            else:
                condition = "LIMIT 1"
                params = ()

            # Получаем фотографию
            query = f"SELECT {photo_column} FROM {self.current_table} {condition}"
            cursor.execute(query, params)
            result = cursor.fetchone()

            if result and result[0]:
                photo_data = result[0]

                if isinstance(photo_data, bytes):
                    # Сохраняем фотографию
                    photo_filename = f"photo_{record_id or 'sample'}.jpg"
                    with open(photo_filename, 'wb') as f:
                        f.write(photo_data)

                    self.update_status(f"✅ Фотография сохранена как: {photo_filename}")

                    # Пытаемся открыть фотографию
                    try:
                        if sys.platform.startswith('win'):
                            os.startfile(photo_filename)
                        elif sys.platform.startswith('darwin'):  # macOS
                            os.system(f'open "{photo_filename}"')
                        else:  # Linux
                            os.system(f'xdg-open "{photo_filename}"')
                        self.update_status("🖼️ Фотография открыта!")
                    except:
                        self.update_status("✅ Фотография сохранена, но не удалось открыть автоматически")
                else:
                    messagebox.showwarning("Предупреждение",
                                           f"Данные в столбце '{photo_column}' не являются бинарными (фотографией)")
            else:
                messagebox.showwarning("Предупреждение", "Фотография не найдена в базе данных")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при извлечении фотографии: {e}")

    def view_selected_image_full(self):
        """Просмотр полноразмерного фото из выделенной ячейки"""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        column = self.tree.identify_column(self.tree.winfo_pointerx() - self.tree.winfo_rootx())

        if not column or column == '#0':
            return

        col_index = int(column.replace('#', '')) - 1
        column_name = self.tree['columns'][col_index]

        if not self.is_image_column(column_name):
            messagebox.showwarning("Предупреждение", "Выбранная колонка не содержит фото!")
            return

        try:
            # Получаем данные из базы данных
            cursor = self.connection.cursor()

            # Находим первичный ключ и его значение
            cursor.execute(f"PRAGMA table_info({self.escape_table_name(self.current_table)})")
            columns_info = cursor.fetchall()
            primary_key_name = columns_info[0][1]

            # Получаем все значения строки
            values = self.tree.item(item, 'values')

            # Находим индекс первичного ключа в отображаемых данных
            pk_index = -1
            for i, col in enumerate(self.tree['columns']):
                if col == primary_key_name:
                    pk_index = i
                    break

            if pk_index != -1 and pk_index < len(values):
                primary_key_value = values[pk_index]

                # Получаем фото из базы данных
                query = f"SELECT {self.escape_table_name(column_name)} FROM {self.escape_table_name(self.current_table)} WHERE {primary_key_name} = ?"
                cursor.execute(query, (primary_key_value,))
                result = cursor.fetchone()

                if result and result[0] and isinstance(result[0], bytes):
                    record_info = f"(ID: {primary_key_value})"
                    self.view_image(column_name, result[0], record_info)
                else:
                    messagebox.showinfo("Информация", "Фото не найдено в базе данных")
            else:
                messagebox.showwarning("Предупреждение", "Не удалось определить запись!")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка получения фото: {str(e)}")

    def export_all_photos(self):
        """Экспорт всех фотографий из таблицы"""
        if not self.current_table:
            messagebox.showwarning("Предупреждение", "Сначала выберите таблицу!")
            return

        try:
            # Спрашиваем директорию для сохранения
            directory = filedialog.askdirectory(title="Выберите папку для сохранения фото")
            if not directory:
                return

            cursor = self.connection.cursor()

            # Получаем информацию о колонках
            cursor.execute(f"PRAGMA table_info({self.escape_table_name(self.current_table)})")
            columns_info = cursor.fetchall()

            photo_columns = []
            for col in columns_info:
                if col[2].upper() == 'BLOB':
                    photo_columns.append(col[1])

            if not photo_columns:
                messagebox.showinfo("Информация", "В таблице нет колонок с фото (BLOB)")
                return

            # Для каждой фото-колонки экспортируем фото
            total_saved = 0
            for col_name in photo_columns:
                # Получаем первичный ключ
                primary_key = columns_info[0][1]

                # Получаем все записи с фото
                query = f"SELECT {primary_key}, {col_name} FROM {self.current_table} WHERE {col_name} IS NOT NULL"
                cursor.execute(query)
                results = cursor.fetchall()

                for row_id, photo_data in results:
                    if isinstance(photo_data, bytes) and len(photo_data) > 100:
                        # Определяем формат изображения
                        try:
                            image = Image.open(io.BytesIO(photo_data))
                            format = image.format.lower() if image.format else 'jpg'
                        except:
                            format = 'jpg'

                        # Создаем имя файла
                        filename = f"{self.current_table}_{col_name}_{row_id}.{format}"
                        filepath = os.path.join(directory, filename)

                        try:
                            with open(filepath, 'wb') as f:
                                f.write(photo_data)
                            total_saved += 1
                        except Exception as e:
                            print(f"Ошибка сохранения {filename}: {e}")

            self.update_status(f"✅ Экспортировано {total_saved} фото в {directory}")
            messagebox.showinfo("Успех", f"Экспортировано {total_saved} фотографий в:\n{directory}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка экспорта фото: {e}")

    def print_image(self, image, title):
        """Печать изображения"""
        if not REPORTLAB_AVAILABLE:
            messagebox.showwarning("Предупреждение", "Модуль reportlab не установлен!")
            return

        file_path = filedialog.asksaveasfilename(
            title="Сохранить фото как PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )

        if file_path:
            try:
                # Сохраняем временное изображение
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
                    image.save(tmp.name, format='JPEG')
                    temp_image_path = tmp.name

                # Создаем PDF
                from reportlab.lib.pagesizes import letter
                from reportlab.lib.utils import ImageReader

                pdf = canvas.Canvas(file_path, pagesize=letter)
                pdf.setTitle(f"Фото - {title}")

                # Добавляем заголовок
                pdf.setFont("Helvetica-Bold", 16)
                pdf.drawString(100, 750, f"Фото: {title}")

                # Добавляем дату
                pdf.setFont("Helvetica", 10)
                pdf.drawString(100, 730, f"Дата: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")

                # Добавляем изображение
                img = ImageReader(temp_image_path)
                pdf.drawImage(img, 100, 400, width=400, height=300, preserveAspectRatio=True)

                # Сохраняем PDF
                pdf.save()

                # Удаляем временный файл
                os.unlink(temp_image_path)

                self.update_status(f"✅ Фото сохранено как PDF: {os.path.basename(file_path)}")

            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка печати фото: {e}")

    def edit_image_dialog(self, column_name, image_data, parent_window):
        """Диалог редактирования изображения"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Редактирование изображения")
        dialog.geometry("500x400")
        dialog.configure(bg='#f5f5f5')

        main_frame = ttk.Frame(dialog, style='Modern.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text="✏️ Редактирование изображения",
                  font=('Segoe UI', 12, 'bold')).pack(pady=10)

        # Загружаем изображение
        image = Image.open(io.BytesIO(image_data))
        self.current_edit_image = image  # Сохраняем для доступа
        photo = ImageTk.PhotoImage(image)

        # Превью
        preview_label = tk.Label(main_frame, image=photo)
        preview_label.image = photo
        self.current_preview_label = preview_label
        preview_label.pack(pady=10)

        # Кнопки редактирования
        button_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        button_frame.pack(fill=tk.X, pady=10)

        def rotate_left():
            self.current_edit_image = self.current_edit_image.rotate(90, expand=True)
            new_photo = ImageTk.PhotoImage(self.current_edit_image)
            self.current_preview_label.config(image=new_photo)
            self.current_preview_label.image = new_photo

        def rotate_right():
            self.current_edit_image = self.current_edit_image.rotate(-90, expand=True)
            new_photo = ImageTk.PhotoImage(self.current_edit_image)
            self.current_preview_label.config(image=new_photo)
            self.current_preview_label.image = new_photo

        def adjust_brightness():
            # Упрощенная регулировка яркости
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Brightness(self.current_edit_image)
            self.current_edit_image = enhancer.enhance(1.2)
            new_photo = ImageTk.PhotoImage(self.current_edit_image)
            self.current_preview_label.config(image=new_photo)
            self.current_preview_label.image = new_photo

        ttk.Button(button_frame, text="↪ Повернуть влево",
                   command=rotate_left).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="↩ Повернуть вправо",
                   command=rotate_right).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🔆 Яркость",
                   command=adjust_brightness).pack(side=tk.LEFT, padx=5)

        # Кнопки сохранения
        save_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        save_frame.pack(fill=tk.X, pady=20)

        def save_changes():
            # Конвертируем обратно в bytes
            img_byte_arr = io.BytesIO()
            self.current_edit_image.save(img_byte_arr, format='JPEG')
            new_image_data = img_byte_arr.getvalue()

            # Здесь можно добавить сохранение в БД
            messagebox.showinfo("Информация", "Изменения применены (в демо-режиме)")
            dialog.destroy()

        ttk.Button(save_frame, text="💾 Сохранить изменения",
                   command=save_changes, style='Success.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(save_frame, text="❌ Отмена",
                   command=dialog.destroy, style='Secondary.TButton').pack(side=tk.LEFT, padx=5)

    def export_excel_with_images_embedded(self):
        """Экспорт в Excel с встроенными миниатюрами изображений"""
        if not self.current_table and not self.joined_tables:
            messagebox.showwarning("Предупреждение", "Нет данных для экспорта!")
            return

        initial_dir = os.path.expanduser("~")

        # Спрашиваем пользователя о параметрах экспорта
        dialog = tk.Toplevel(self.root)
        dialog.title("Настройки экспорта")
        dialog.geometry("400x300")
        dialog.configure(bg='#f5f5f5')
        dialog.transient(self.root)
        dialog.grab_set()

        main_frame = ttk.Frame(dialog, style='Modern.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text="⚙️ Настройки экспорта фото",
                  font=('Segoe UI', 12, 'bold')).pack(pady=10)

        # Опции экспорта
        self.export_include_images = tk.BooleanVar(value=True)
        self.export_image_size = tk.IntVar(value=100)
        self.export_save_as_files = tk.BooleanVar(value=False)

        ttk.Checkbutton(main_frame, text="Включать фото в Excel",
                        variable=self.export_include_images).pack(anchor=tk.W, pady=5)

        ttk.Checkbutton(main_frame, text="Сохранять фото как отдельные файлы",
                        variable=self.export_save_as_files).pack(anchor=tk.W, pady=5)

        ttk.Label(main_frame, text="Размер миниатюр (пикселей):").pack(anchor=tk.W, pady=5)
        size_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        size_frame.pack(fill=tk.X, pady=5)

        ttk.Radiobutton(size_frame, text="Маленькие (80px)", variable=self.export_image_size,
                        value=80).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(size_frame, text="Средние (100px)", variable=self.export_image_size,
                        value=100).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(size_frame, text="Большие (150px)", variable=self.export_image_size,
                        value=150).pack(side=tk.LEFT, padx=5)

        # Кнопки
        buttons_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        buttons_frame.pack(fill=tk.X, pady=20)

        def proceed():
            dialog.destroy()
            self.perform_excel_export_with_images()

        ttk.Button(buttons_frame, text="✅ Продолжить", command=proceed,
                   style='Success.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="❌ Отмена", command=dialog.destroy,
                   style='Secondary.TButton').pack(side=tk.LEFT, padx=5)

        self.root.wait_window(dialog)

    def perform_excel_export_with_images(self):
        """Выполняет экспорт в Excel с изображениями - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        file_path = filedialog.asksaveasfilename(
            title="Сохранить как Excel",
            defaultextension=".xlsx",
            initialdir=os.path.expanduser("~"),
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            query, display_columns = self.build_query()
            cursor = self.connection.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()

            from openpyxl import Workbook
            from openpyxl.drawing.image import Image as ExcelImage
            from openpyxl.utils import get_column_letter
            import tempfile

            wb = Workbook()
            ws = wb.active
            ws.title = self.current_table or "Данные"

            # Записываем заголовки
            for col_idx, col_name in enumerate(display_columns, 1):
                ws.cell(row=1, column=col_idx, value=col_name)
                col_letter = get_column_letter(col_idx)
                ws.column_dimensions[col_letter].width = 15

            photo_count = 0
            saved_files = []
            temp_files = []

            # Создаем временную директорию для фото
            temp_dir = tempfile.mkdtemp(prefix="excel_export_")

            try:
                # Обрабатываем данные
                for row_idx, row in enumerate(rows, 2):
                    for col_idx, value in enumerate(row, 1):
                        col_name = display_columns[col_idx - 1]

                        if (col_name in self.image_columns and
                                value is not None and
                                isinstance(value, bytes) and
                                self.export_include_images.get()):

                            try:
                                if self.is_valid_image_blob(value):
                                    # Создаем временный файл в нашей временной директории
                                    temp_file = os.path.join(temp_dir, f"photo_{row_idx}_{col_idx}.png")

                                    with open(temp_file, 'wb') as f:
                                        f.write(value)
                                    temp_files.append(temp_file)

                                    if self.export_save_as_files.get():
                                        # Сохраняем как отдельный файл рядом с Excel
                                        save_dir = os.path.dirname(file_path) or "."
                                        photo_filename = f"{self.current_table}_row{row_idx - 1}_{col_name}.png"
                                        photo_path = os.path.join(save_dir, photo_filename)

                                        # Создаем директорию, если её нет
                                        os.makedirs(save_dir, exist_ok=True)

                                        import shutil
                                        shutil.copy2(temp_file, photo_path)
                                        saved_files.append(photo_path)
                                        ws.cell(row=row_idx, column=col_idx, value=f"📷 {photo_filename}")
                                    else:
                                        # Вставляем изображение в Excel
                                        try:
                                            img = ExcelImage(temp_file)
                                            img_size = self.export_image_size.get()
                                            img.width = img_size
                                            img.height = img_size

                                            cell_coord = f"{get_column_letter(col_idx)}{row_idx}"
                                            ws.add_image(img, cell_coord)
                                            ws.row_dimensions[row_idx].height = img_size * 0.75
                                            photo_count += 1
                                        except Exception as img_error:
                                            ws.cell(row=row_idx, column=col_idx,
                                                    value=f"[Ошибка: {str(img_error)[:30]}]")

                                else:
                                    ws.cell(row=row_idx, column=col_idx, value="[Невалидное изображение]")

                            except Exception as e:
                                ws.cell(row=row_idx, column=col_idx, value=f"[Ошибка: {str(e)[:30]}]")

                        elif col_name in self.image_columns and value is not None:
                            ws.cell(row=row_idx, column=col_idx, value="🖼️ Фото")

                        elif isinstance(value, bool):
                            ws.cell(row=row_idx, column=col_idx, value="✅ Да" if value else "❌ Нет")

                        elif value is None:
                            ws.cell(row=row_idx, column=col_idx, value="")

                        else:
                            ws.cell(row=row_idx, column=col_idx, value=str(value))

                # Создаем лист с информацией
                ws_info = wb.create_sheet(title="Информация")
                ws_info['A1'] = "Отчет об экспорте"
                ws_info['A3'] = f"Таблица: {self.current_table}"
                ws_info['A4'] = f"Файл базы данных: {os.path.basename(self.db_name)}"
                ws_info['A5'] = f"Дата экспорта: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}"
                ws_info['A6'] = f"Всего строк: {len(rows)}"
                ws_info['A7'] = f"Всего колонок: {len(display_columns)}"
                ws_info['A8'] = f"Фото в экспорте: {photo_count}"

                if saved_files:
                    ws_info['A10'] = "Сохраненные файлы фото:"
                    for i, file_path in enumerate(saved_files, start=11):
                        ws_info[f'A{i}'] = os.path.basename(file_path)

                # Сохраняем файл
                wb.save(file_path)

                # Показываем отчет
                report = f"✅ Экспорт завершен успешно!\n\n"
                report += f"Файл: {os.path.basename(file_path)}\n"
                report += f"Расположение: {os.path.dirname(file_path)}\n"
                report += f"Строк данных: {len(rows)}\n"
                report += f"Колонок: {len(display_columns)}\n"

                if self.export_include_images.get():
                    if self.export_save_as_files.get():
                        report += f"Фото сохранены как файлы: {len(saved_files)}\n"
                    else:
                        report += f"Фото встроены в Excel: {photo_count}\n"

                self.update_status(f"✅ Экспорт завершен: {os.path.basename(file_path)}")
                messagebox.showinfo("Успешный экспорт", report)

            finally:
                # Очищаем временные файлы
                for temp_file in temp_files:
                    try:
                        if os.path.exists(temp_file):
                            os.unlink(temp_file)
                    except:
                        pass

                # Удаляем временную директорию
                try:
                    if os.path.exists(temp_dir):
                        os.rmdir(temp_dir)
                except:
                    pass

        except PermissionError as e:
            messagebox.showerror("Ошибка доступа",
                                 f"Нет прав доступа к файлу:\n{file_path}\n\n"
                                 f"Сохраните файл в другую папку (например, Документы или Рабочий стол)")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка экспорта: {str(e)}")

    def export_excel_simple(self):
        """Экспорт в Excel с текстовыми ссылками на фото"""
        if not self.current_table and not self.joined_tables:
            messagebox.showwarning("Предупреждение", "Нет данных для экспорта!")
            return

        initial_dir = os.path.expanduser("~")

        # Спрашиваем о методе экспорта
        export_method = messagebox.askyesno("Метод экспорта",
                                            "Хотите ли вы экспортировать фото как файлы?\n\n"
                                            "✅ Да - фото будут сохранены как отдельные файлы\n"
                                            "❌ Нет - в Excel будут только ссылки на фото")

        file_path = filedialog.asksaveasfilename(
            title="Сохранить как Excel",
            defaultextension=".xlsx",
            initialdir=initial_dir,
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            query, display_columns = self.build_query()
            cursor = self.connection.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()

            # Создаем DataFrame для экспорта
            export_data = []
            photo_files = []  # Список сохраненных фото файлов

            for row_idx, row in enumerate(rows):
                row_data = {}
                for col_idx, value in enumerate(row):
                    col_name = display_columns[col_idx]

                    if col_name in self.image_columns and value is not None and isinstance(value, bytes):
                        if export_method:  # Сохраняем фото как файлы
                            try:
                                if self.is_valid_image_blob(value):
                                    # Создаем имя файла для фото
                                    photo_filename = f"{self.current_table}_row{row_idx + 1}_{col_name}.png"
                                    photo_path = os.path.join(os.path.dirname(file_path), photo_filename)

                                    # Сохраняем фото
                                    with open(photo_path, 'wb') as f:
                                        f.write(value)
                                    photo_files.append(photo_path)

                                    # В Excel записываем имя файла
                                    row_data[col_name] = f"📷 {photo_filename}"
                                else:
                                    row_data[col_name] = "[BLOB данные]"
                            except Exception as e:
                                row_data[col_name] = f"[Ошибка фото]"
                        else:  # Просто указываем наличие фото
                            if self.is_valid_image_blob(value):
                                row_data[col_name] = "🖼️ Фото (в базе данных)"
                            else:
                                row_data[col_name] = "[BLOB данные]"

                    elif isinstance(value, bool):
                        row_data[col_name] = "Да" if value else "Нет"

                    elif value is None:
                        row_data[col_name] = ""

                    else:
                        row_data[col_name] = str(value)

                export_data.append(row_data)

            df = pd.DataFrame(export_data, columns=display_columns)

            # Создаем директорию, если она не существует
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

            # Экспортируем в Excel
            df.to_excel(file_path, index=False, engine='openpyxl')

            # Если экспортировали фото как файлы, добавляем информацию об этом
            if export_method and photo_files:
                # Добавляем лист с информацией о фото
                from openpyxl import load_workbook
                wb = load_workbook(file_path)
                ws_info = wb.create_sheet(title="Файлы фото")

                ws_info['A1'] = "Список файлов с фотографиями"
                ws_info['A2'] = "Путь к файлу"
                ws_info['B2'] = "Размер (байт)"

                for i, photo_path in enumerate(photo_files, start=3):
                    ws_info[f'A{i}'] = os.path.basename(photo_path)
                    ws_info[f'B{i}'] = os.path.getsize(photo_path) if os.path.exists(photo_path) else "Не найден"

                wb.save(file_path)

            # Создаем отчет
            report = f"✅ Экспорт завершен успешно!\n\n"
            report += f"Файл: {file_path}\n"
            report += f"Строк: {len(rows)}\n"
            report += f"Колонок: {len(display_columns)}\n"

            if export_method:
                report += f"Фото сохранены как файлы: {len(photo_files)}\n\n"
                report += "💡 Фотографии сохранены в той же папке, что и Excel файл."
            else:
                report += "\n💡 Фотографии отмечены как '🖼️ Фото (в базе данных)'"

            messagebox.showinfo("Успех", report)
            self.update_status(f"✅ Данные экспортированы в {os.path.basename(file_path)}")

        except PermissionError as e:
            messagebox.showerror("Ошибка доступа",
                                 f"Нет прав доступа к файлу:\n{file_path}\n\n"
                                 f"Сохраните файл в другую папку (например, Документы или Рабочий стол)")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка экспорта в Excel: {e}")
# КЛАССЫ ДИАЛОГОВ

class ModernAddColumnDialog:
    def __init__(self, parent, app):
        self.app = app
        self.top = tk.Toplevel(parent)
        self.top.title("Добавить колонку")
        self.top.geometry("400x300")
        self.top.configure(bg='#f5f5f5')
        self.top.transient(parent)
        self.top.grab_set()
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.top, style='Modern.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text=f"Добавить колонку в таблицу '{self.app.current_table}'",
                  font=('Segoe UI', 12, 'bold')).pack(pady=10)

        ttk.Label(main_frame, text="Имя колонки:").pack(anchor=tk.W, pady=5)
        self.column_name = ttk.Entry(main_frame, style='Modern.TEntry', width=30)
        self.column_name.pack(fill=tk.X, pady=5)

        ttk.Label(main_frame, text="Тип данных:").pack(anchor=tk.W, pady=5)
        self.column_type = ttk.Combobox(main_frame, values=["TEXT", "INTEGER", "REAL", "BOOLEAN", "BLOB"],
                                        state="readonly", style='Modern.TCombobox')
        self.column_type.set("TEXT")
        self.column_type.pack(fill=tk.X, pady=5)

        ttk.Label(main_frame, text="Значение по умолчанию (необязательно):").pack(anchor=tk.W, pady=5)
        self.default_value = ttk.Entry(main_frame, style='Modern.TEntry', width=30)
        self.default_value.pack(fill=tk.X, pady=5)

        help_label = ttk.Label(main_frame,
                               text="💡 TEXT - текст\n💡 INTEGER - целые числа\n💡 REAL - дробные числа\n💡 BOOLEAN - да/нет\n💡 BLOB - фото и файлы",
                               font=('Segoe UI', 8), foreground="gray")
        help_label.pack(pady=5)

        buttons_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        buttons_frame.pack(fill=tk.X, pady=20)

        ttk.Button(buttons_frame, text="✅ Добавить", command=self.add_column,
                   style='Success.TButton').pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="❌ Отмена", command=self.top.destroy,
                   style='Secondary.TButton').pack(side=tk.LEFT, padx=10)

        self.top.bind('<Return>', lambda e: self.add_column())

    def add_column(self):
        column_name = self.column_name.get().strip()
        column_type = self.column_type.get()
        default_value = self.default_value.get().strip()

        if not column_name:
            messagebox.showwarning("Предупреждение", "Введите имя колонки!")
            return

        if not column_type:
            messagebox.showwarning("Предупреждение", "Выберите тип данных!")
            return

        try:
            cursor = self.app.connection.cursor()
            cursor.execute(f"PRAGMA table_info({self.app.escape_table_name(self.app.current_table)})")
            existing_columns = [col[1] for col in cursor.fetchall()]

            if column_name in existing_columns:
                messagebox.showerror("Ошибка", f"Колонка с именем '{column_name}' уже существует!")
                return

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка проверки существующих колонок: {e}")
            return

        default_val = default_value if default_value else None
        self.app.add_column_to_table(column_name, column_type, default_val)
        self.top.destroy()


class ModernBooleanEditDialog:
    def __init__(self, parent, column_name, current_value):
        self.top = tk.Toplevel(parent)
        self.top.title(f"Редактирование {column_name}")
        self.top.geometry("300x150")
        self.top.configure(bg='#f5f5f5')
        self.top.transient(parent)
        self.top.grab_set()

        self.result = None

        ttk.Label(self.top, text=f"Выберите значение для '{column_name}':",
                  font=('Segoe UI', 10, 'bold')).pack(pady=10)

        current_bool = False
        if current_value in ['1', 1, 'True', 'true', 'Да', 'да', '✅ Да']:
            current_bool = True

        self.bool_var = tk.BooleanVar(value=current_bool)

        radio_frame = ttk.Frame(self.top, style='Modern.TFrame')
        radio_frame.pack(pady=10)

        ttk.Radiobutton(radio_frame, text="✅ Да", variable=self.bool_var,
                        value=True).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(radio_frame, text="❌ Нет", variable=self.bool_var,
                        value=False).pack(side=tk.LEFT, padx=10)

        buttons_frame = ttk.Frame(self.top, style='Modern.TFrame')
        buttons_frame.pack(pady=10)

        ttk.Button(buttons_frame, text="✅ OK", command=self.ok,
                   style='Success.TButton').pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="❌ Отмена", command=self.cancel,
                   style='Secondary.TButton').pack(side=tk.LEFT, padx=10)

        self.top.bind('<Return>', lambda e: self.ok())

    def ok(self):
        self.result = "True" if self.bool_var.get() else "False"
        self.top.destroy()

    def cancel(self):
        self.result = None
        self.top.destroy()


class ModernMultiTableSelectDialog:
    def __init__(self, parent, app, available_tables):
        self.app = app
        self.available_tables = available_tables
        self.selected_tables = []

        self.top = tk.Toplevel(parent)
        self.top.title("Выбор таблиц для соединения")
        self.top.geometry("400x500")
        self.top.configure(bg='#f5f5f5')
        self.top.transient(parent)
        self.top.grab_set()

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.top, style='Modern.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text="🔗 Выберите таблицы для соединения",
                  font=('Segoe UI', 12, 'bold')).pack(pady=10)

        ttk.Label(main_frame, text=f"Основная таблица: {self.app.current_table}",
                  font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W, pady=10)

        ttk.Label(main_frame, text="Доступные таблицы:").pack(anchor=tk.W, pady=5)

        # Фрейм для списка таблиц с чекбоксами
        list_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Создаем Canvas и Scrollbar для прокрутки
        canvas = tk.Canvas(list_frame, bg='#f5f5f5', highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='Modern.TFrame')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        self.checkbox_vars = {}

        # Создаем чекбоксы для каждой таблицы
        for i, table_name in enumerate(self.available_tables):
            var = tk.BooleanVar()
            cb = ttk.Checkbutton(scrollable_frame, text=table_name, variable=var)
            cb.grid(row=i, column=0, sticky=tk.W, pady=2, padx=5)
            self.checkbox_vars[table_name] = var

        # Кнопки выбора
        button_frame = ttk.Frame(scrollable_frame, style='Modern.TFrame')
        button_frame.grid(row=len(self.available_tables), column=0, sticky=tk.W + tk.E, pady=10)

        ttk.Button(button_frame, text="✅ Выбрать все", command=self.select_all,
                   style='Success.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="❌ Снять все", command=self.deselect_all,
                   style='Secondary.TButton').pack(side=tk.LEFT, padx=5)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Информация о предстоящих соединениях
        info_label = ttk.Label(main_frame,
                               text="ℹ️ Будут автоматически соединены по общим полям",
                               font=('Segoe UI', 9), foreground="gray")
        info_label.pack(pady=5)

        # Кнопки диалога
        dialog_buttons = ttk.Frame(main_frame, style='Modern.TFrame')
        dialog_buttons.pack(fill=tk.X, pady=10)

        ttk.Button(dialog_buttons, text="🔗 Соединить выбранные", command=self.join_selected,
                   style='Success.TButton').pack(side=tk.LEFT, padx=10)
        ttk.Button(dialog_buttons, text="❌ Отмена", command=self.top.destroy,
                   style='Secondary.TButton').pack(side=tk.LEFT, padx=10)

    def select_all(self):
        """Выбрать все таблицы"""
        for var in self.checkbox_vars.values():
            var.set(True)

    def deselect_all(self):
        """Снять выбор со всех таблиц"""
        for var in self.checkbox_vars.values():
            var.set(False)

    def join_selected(self):
        """Соединить выбранные таблицы"""
        self.selected_tables = []
        for table_name, var in self.checkbox_vars.items():
            if var.get():
                self.selected_tables.append(table_name)

        if not self.selected_tables:
            messagebox.showwarning("Предупреждение", "Выберите хотя бы одну таблицу!")
            return

        self.top.destroy()


class ModernExcelImportDialog:
    def __init__(self, parent, app, excel_columns):
        self.app = app
        self.excel_columns = excel_columns
        self.proceed = False

        self.top = tk.Toplevel(parent)
        self.top.title("Импорт из Excel")
        self.top.geometry("500x400")
        self.top.configure(bg='#f5f5f5')
        self.top.transient(parent)
        self.top.grab_set()

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.top, style='Modern.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text="📥 Импорт данных из Excel",
                  font=('Segoe UI', 12, 'bold')).pack(pady=10)

        # Информация о таблицах
        info_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        info_frame.pack(fill=tk.X, pady=10)

        ttk.Label(info_frame, text=f"Целевая таблица: {self.app.current_table}",
                  font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)

        ttk.Label(info_frame, text=f"Колонки в Excel: {len(self.excel_columns)}").pack(anchor=tk.W)

        # Предупреждение
        warning_label = ttk.Label(main_frame,
                                  text="⚠️ Убедитесь, что структура Excel соответствует структуре таблицы!",
                                  font=('Segoe UI', 9), foreground="orange")
        warning_label.pack(pady=10)

        # Список колонок
        ttk.Label(main_frame, text="Колонки в файле Excel:").pack(anchor=tk.W, pady=5)

        list_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        columns_listbox = tk.Listbox(list_frame, bg='white', bd=0, font=('Segoe UI', 9))
        columns_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for col in self.excel_columns:
            columns_listbox.insert(tk.END, col)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        columns_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=columns_listbox.yview)

        # Кнопки
        buttons_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        buttons_frame.pack(fill=tk.X, pady=10)

        ttk.Button(buttons_frame, text="✅ Импортировать", command=self.import_data,
                   style='Success.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="❌ Отмена", command=self.top.destroy,
                   style='Secondary.TButton').pack(side=tk.LEFT, padx=5)

    def import_data(self):
        self.proceed = True
        self.top.destroy()


class ModernJoinTablesDialog:
    def __init__(self, parent, app):
        self.app = app
        self.top = tk.Toplevel(parent)
        self.top.title("Соединить таблицы")
        self.top.geometry("500x400")
        self.top.configure(bg='#f5f5f5')
        self.top.transient(parent)
        self.top.grab_set()
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.top, style='Modern.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text="🔗 Соединение таблиц",
                  font=('Segoe UI', 12, 'bold')).pack(pady=10)

        ttk.Label(main_frame, text=f"Основная таблица: {self.app.current_table}",
                  font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W, pady=10)

        # Выбор второй таблицы
        ttk.Label(main_frame, text="Таблица для соединения:").pack(anchor=tk.W, pady=5)
        self.table2_var = tk.StringVar()
        self.table2_combo = ttk.Combobox(main_frame, textvariable=self.table2_var,
                                         state="readonly", width=20)

        tables = []
        for i in range(self.app.table_listbox.size()):
            table = self.app.table_listbox.get(i)
            if table != self.app.current_table:
                tables.append(table)

        self.table2_combo['values'] = tables
        if tables:
            self.table2_combo.set(tables[0])
        self.table2_combo.pack(fill=tk.X, pady=5)

        # Атрибуты
        ttk.Label(main_frame, text="Атрибут из основной таблицы:").pack(anchor=tk.W, pady=5)
        self.attr1_combo = ttk.Combobox(main_frame, state="readonly", width=20)
        self.attr1_combo.pack(fill=tk.X, pady=5)

        ttk.Label(main_frame, text="Атрибут из второй таблицы:").pack(anchor=tk.W, pady=5)
        self.attr2_combo = ttk.Combobox(main_frame, state="readonly", width=20)
        self.attr2_combo.pack(fill=tk.X, pady=5)

        # Тип соединения
        ttk.Label(main_frame, text="Тип соединения:").pack(anchor=tk.W, pady=5)
        self.join_type = ttk.Combobox(main_frame, values=["INNER JOIN", "LEFT JOIN"],
                                      state="readonly", width=20)
        self.join_type.set("INNER JOIN")
        self.join_type.pack(fill=tk.X, pady=5)

        self.table2_combo.bind('<<ComboboxSelected>>', self.update_attributes)
        self.update_attributes()

        # Предпросмотр
        ttk.Label(main_frame, text="Предпросмотр запроса:").pack(anchor=tk.W, pady=(20, 5))
        self.query_preview = tk.Text(main_frame, height=4, width=50, bg='white', bd=0)
        self.query_preview.pack(fill=tk.X, pady=5)

        self.table2_combo.bind('<<ComboboxSelected>>', self.update_query_preview)
        self.attr1_combo.bind('<<ComboboxSelected>>', self.update_query_preview)
        self.attr2_combo.bind('<<ComboboxSelected>>', self.update_query_preview)
        self.join_type.bind('<<ComboboxSelected>>', self.update_query_preview)

        buttons_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        buttons_frame.pack(fill=tk.X, pady=20)

        ttk.Button(buttons_frame, text="🔗 Соединить", command=self.join_tables,
                   style='Success.TButton').pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="❌ Отмена", command=self.top.destroy,
                   style='Secondary.TButton').pack(side=tk.LEFT, padx=10)

        self.update_query_preview()

    def update_attributes(self, event=None):
        try:
            cursor = self.app.connection.cursor()

            cursor.execute(f"PRAGMA table_info({self.app.escape_table_name(self.app.current_table)})")
            table1_attrs = [col[1] for col in cursor.fetchall()]
            self.attr1_combo['values'] = table1_attrs
            if table1_attrs:
                self.attr1_combo.set(table1_attrs[0])

            table2 = self.table2_combo.get()
            if table2:
                cursor.execute(f"PRAGMA table_info({self.app.escape_table_name(table2)})")
                table2_attrs = [col[1] for col in cursor.fetchall()]
                self.attr2_combo['values'] = table2_attrs
                if table2_attrs:
                    self.attr2_combo.set(table2_attrs[0])

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка получения атрибутов: {e}")

    def update_query_preview(self, event=None):
        table2 = self.table2_combo.get()
        attr1 = self.attr1_combo.get()
        attr2 = self.attr2_combo.get()
        join_type = self.join_type.get().split()[0]

        if table2 and attr1 and attr2:
            query = f"SELECT *\nFROM {self.app.escape_table_name(self.app.current_table)}\n{join_type} JOIN {self.app.escape_table_name(table2)}\nON {self.app.current_table}.{attr1} = {table2}.{attr2}"
            self.query_preview.delete(1.0, tk.END)
            self.query_preview.insert(tk.END, query)

    def join_tables(self):
        table2 = self.table2_combo.get()
        attr1 = self.attr1_combo.get()
        attr2 = self.attr2_combo.get()
        join_type = self.join_type.get().split()[0]

        if not table2 or not attr1 or not attr2:
            messagebox.showwarning("Предупреждение", "Заполните все поля!")
            return

        if self.app.join_tables(table2, attr1, attr2, join_type):
            self.top.destroy()


class ModernSelectAttributesDialog:
    def __init__(self, parent, app):
        self.app = app
        self.top = tk.Toplevel(parent)
        self.top.title("Выбор атрибутов для отображения")
        self.top.geometry("500x600")
        self.top.configure(bg='#f5f5f5')
        self.top.transient(parent)
        self.top.grab_set()

        self.selected_attributes = self.app.selected_attributes.copy()
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.top, style='Modern.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text="👁️ Выберите атрибуты для отображения",
                  font=('Segoe UI', 12, 'bold')).pack(pady=10)

        ttk.Label(main_frame, text="Доступные атрибуты:").pack(anchor=tk.W, pady=5)

        checkboxes_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        checkboxes_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(checkboxes_frame, bg='#f5f5f5', highlightthickness=0)
        scrollbar = ttk.Scrollbar(checkboxes_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='Modern.TFrame')

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        all_columns = self.app.get_all_tables_columns()
        self.checkbox_vars = {}

        row = 0
        for table_name, columns in all_columns.items():
            ttk.Label(scrollable_frame, text=f"📋 Таблица: {table_name}",
                      font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky=tk.W, pady=(10, 5))
            row += 1

            for column in columns:
                var = tk.BooleanVar()
                full_attr_name = f"{table_name}.{column}"
                var.set(full_attr_name in self.selected_attributes)

                cb = ttk.Checkbutton(scrollable_frame, text=column, variable=var)
                cb.grid(row=row, column=0, sticky=tk.W, pady=2)

                self.checkbox_vars[full_attr_name] = var
                row += 1

        buttons_frame = ttk.Frame(scrollable_frame, style='Modern.TFrame')
        buttons_frame.grid(row=row, column=0, sticky=tk.W + tk.E, pady=20)

        ttk.Button(buttons_frame, text="✅ Выбрать все", command=self.select_all,
                   style='Success.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="❌ Снять все", command=self.deselect_all,
                   style='Secondary.TButton').pack(side=tk.LEFT, padx=5)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        dialog_buttons = ttk.Frame(main_frame, style='Modern.TFrame')
        dialog_buttons.pack(fill=tk.X, pady=10)

        ttk.Button(dialog_buttons, text="✅ Применить", command=self.apply_selection,
                   style='Success.TButton').pack(side=tk.LEFT, padx=10)
        ttk.Button(dialog_buttons, text="❌ Отмена", command=self.top.destroy,
                   style='Secondary.TButton').pack(side=tk.LEFT, padx=10)
        ttk.Button(dialog_buttons, text="👁️ Показать все", command=self.show_all,
                   style='Primary.TButton').pack(side=tk.LEFT, padx=10)

    def select_all(self):
        for var in self.checkbox_vars.values():
            var.set(True)

    def deselect_all(self):
        for var in self.checkbox_vars.values():
            var.set(False)

    def show_all(self):
        self.selected_attributes = []
        self.apply_selection()

    def apply_selection(self):
        selected = []
        for attr_name, var in self.checkbox_vars.items():
            if var.get():
                selected.append(attr_name)

        self.app.set_selected_attributes(selected)
        self.top.destroy()


class ModernCreateTableDialog:
    def __init__(self, parent, app):
        self.app = app
        self.top = tk.Toplevel(parent)
        self.top.title("Создать таблицу")
        self.top.geometry("600x500")
        self.top.configure(bg='#f5f5f5')
        self.top.transient(parent)
        self.top.grab_set()

        # Делаем окно изменяемым и устанавливаем минимальный размер
        self.top.resizable(True, True)
        self.top.minsize(450, 350)

        self.columns = []
        self.create_widgets()

    def create_widgets(self):
        # Создаем главный фрейм с padding и настройкой весов для расширения
        main_frame = ttk.Frame(self.top, style='Modern.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Настраиваем сетку main_frame для правильного расширения
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(main_frame, text="📊 Создание новой таблицы",
                  font=('Segoe UI', 14, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 10))

        # Фрейм для названия таблицы
        name_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        name_frame.grid(row=1, column=0, sticky=tk.W + tk.E, pady=(0, 10))
        name_frame.columnconfigure(1, weight=1)

        ttk.Label(name_frame, text="Название таблицы:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.table_name = ttk.Entry(name_frame, style='Modern.TEntry', font=('Segoe UI', 10))
        self.table_name.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=(10, 0))

        # Фрейм для списка колонок с расширением
        columns_frame = ttk.LabelFrame(main_frame, text="📋 Колонки таблицы",
                                       style='Modern.TLabelframe')
        columns_frame.grid(row=2, column=0, sticky=tk.NSEW, pady=(0, 20))

        # Настраиваем сетку columns_frame
        columns_frame.grid_rowconfigure(0, weight=1)
        columns_frame.grid_columnconfigure(0, weight=1)

        # Контейнер для списка и кнопок
        list_container = ttk.Frame(columns_frame, style='Modern.TFrame')
        list_container.grid(row=0, column=0, sticky=tk.NSEW, padx=10, pady=10)

        # Настраиваем сетку list_container
        list_container.grid_rowconfigure(0, weight=1)
        list_container.grid_columnconfigure(0, weight=1)

        # Список колонок
        self.columns_listbox = tk.Listbox(list_container, bg='white', bd=0, font=('Segoe UI', 9))
        self.columns_listbox.grid(row=0, column=0, sticky=tk.NSEW)

        # Полоса прокрутки
        list_scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL)
        list_scrollbar.grid(row=0, column=1, sticky=tk.NS)
        self.columns_listbox.config(yscrollcommand=list_scrollbar.set)
        list_scrollbar.config(command=self.columns_listbox.yview)

        # Фрейм для кнопок управления колонками
        col_buttons_frame = ttk.Frame(columns_frame, style='Modern.TFrame')
        col_buttons_frame.grid(row=1, column=0, sticky=tk.EW, padx=10, pady=(0, 10))

        ttk.Button(col_buttons_frame, text="➕ Добавить колонку", command=self.add_column_dialog,
                   style='Primary.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(col_buttons_frame, text="🗑️ Удалить колонку", command=self.remove_column,
                   style='Danger.TButton').pack(side=tk.LEFT)

        # Фрейм для кнопок диалога
        dialog_buttons = ttk.Frame(main_frame, style='Modern.TFrame')
        dialog_buttons.grid(row=3, column=0, sticky=tk.EW, pady=(10, 0))

        ttk.Button(dialog_buttons, text="✅ Создать таблицу", command=self.create_table,
                   style='Success.TButton').pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(dialog_buttons, text="❌ Отмена", command=self.top.destroy,
                   style='Secondary.TButton').pack(side=tk.RIGHT)

    def add_column_dialog(self):
        dialog = tk.Toplevel(self.top)
        dialog.title("Добавить колонку")
        dialog.geometry("400x250")
        dialog.configure(bg='#f5f5f5')
        dialog.transient(self.top)
        dialog.grab_set()

        # Делаем окно диалога также изменяемым
        dialog.resizable(False, False)  # Окно добавления колонки оставляем фиксированным
        dialog.minsize(350, 200)

        main_frame = ttk.Frame(dialog, style='Modern.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Настраиваем сетку для расширения
        main_frame.columnconfigure(0, weight=1)

        ttk.Label(main_frame, text="➕ Новая колонка", font=('Segoe UI', 12, 'bold')).pack(pady=(0, 15))

        ttk.Label(main_frame, text="Имя колонки:").pack(anchor=tk.W, pady=(5, 0))
        name_entry = ttk.Entry(main_frame, style='Modern.TEntry', font=('Segoe UI', 10))
        name_entry.pack(fill=tk.X, pady=(5, 10))

        ttk.Label(main_frame, text="Тип данных:").pack(anchor=tk.W, pady=(5, 0))
        type_combo = ttk.Combobox(main_frame, values=["TEXT", "INTEGER", "REAL", "BOOLEAN", "BLOB"],
                                  state="readonly", style='Modern.TCombobox')
        type_combo.set("TEXT")
        type_combo.pack(fill=tk.X, pady=(5, 15))

        def add_column():
            name = name_entry.get().strip()
            if name:
                column = {"name": name, "type": type_combo.get()}
                self.columns.append(column)
                self.columns_listbox.insert(tk.END, f"{name} ({type_combo.get()})")
                dialog.destroy()
            else:
                messagebox.showwarning("Предупреждение", "Введите имя колонки!")

        button_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="✅ Добавить", command=add_column,
                   style='Success.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="❌ Отмена", command=dialog.destroy,
                   style='Secondary.TButton').pack(side=tk.LEFT)

        name_entry.focus()

    def remove_column(self):
        selection = self.columns_listbox.curselection()
        if selection:
            index = selection[0]
            self.columns_listbox.delete(index)
            self.columns.pop(index)

    def create_table(self):
        table_name = self.table_name.get().strip()
        if not table_name:
            messagebox.showwarning("Предупреждение", "Введите название таблицы!")
            return

        if not self.columns:
            messagebox.showwarning("Предупреждение", "Добавьте хотя бы одну колонку!")
            return

        self.app.create_table(table_name, self.columns)
        self.top.destroy()


class ModernAddRecordDialog:
    def __init__(self, parent, app):
        self.app = app
        self.top = tk.Toplevel(parent)
        self.top.title("Добавить запись")
        self.top.geometry("400x500")
        self.top.configure(bg='#f5f5f5')
        self.top.transient(parent)
        self.top.grab_set()

        self.entries = {}
        self.create_widgets()

    def create_widgets(self):
        try:
            cursor = self.app.connection.cursor()
            cursor.execute(f"PRAGMA table_info({self.app.escape_table_name(self.app.current_table)})")
            columns = cursor.fetchall()

            main_frame = ttk.Frame(self.top, style='Modern.TFrame')
            main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

            ttk.Label(main_frame, text=f"➕ Добавить запись в '{self.app.current_table}'",
                      font=('Segoe UI', 12, 'bold')).pack(pady=10)

            input_frame = ttk.Frame(main_frame, style='Modern.TFrame')
            input_frame.pack(fill=tk.BOTH, expand=True)

            for i, column in enumerate(columns):
                col_name = column[1]
                col_type = column[2]

                ttk.Label(input_frame, text=f"{col_name} ({col_type}):").grid(
                    row=i, column=0, sticky=tk.W, pady=5)

                if col_type.upper() == 'BOOLEAN':
                    entry = ttk.Combobox(input_frame, values=["True", "False", "1", "0", "Да", "Нет"],
                                         state="readonly", width=18)
                    entry.set("False")
                else:
                    entry = ttk.Entry(input_frame, width=20)

                entry.grid(row=i, column=1, sticky=tk.EW, pady=5, padx=(10, 0))
                self.entries[col_name] = (entry, col_type)
                input_frame.columnconfigure(1, weight=1)

            help_label = ttk.Label(main_frame, text="Для BOOLEAN: True/1/Да или False/0/Нет",
                                   font=('Segoe UI', 8), foreground="gray")
            help_label.pack(pady=5)

            buttons_frame = ttk.Frame(main_frame, style='Modern.TFrame')
            buttons_frame.pack(pady=10)

            ttk.Button(buttons_frame, text="✅ Добавить", command=self.add_record,
                       style='Success.TButton').pack(side=tk.LEFT, padx=5)
            ttk.Button(buttons_frame, text="❌ Отмена", command=self.top.destroy,
                       style='Secondary.TButton').pack(side=tk.LEFT, padx=5)

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка получения структуры таблицы: {e}")
            self.top.destroy()

    def add_record(self):
        values = []
        for col_name, (entry, col_type) in self.entries.items():
            if hasattr(entry, 'get'):
                value = entry.get().strip()
            else:
                value = ""

            if value == "":
                values.append(None)
            elif col_type.upper() == 'BOOLEAN':
                value_lower = value.lower()
                if value_lower in ['true', '1', 'да', 'yes']:
                    values.append(1)
                elif value_lower in ['false', '0', 'нет', 'no']:
                    values.append(0)
                else:
                    values.append(None)
            else:
                values.append(value)

        self.app.add_record(values)
        self.top.destroy()


def main():
    root = tk.Tk()
    app = ModernDatabaseApp(root)
    root.mainloop()

    if app.connection:
        app.connection.close()


if __name__ == "__main__":
    main()