import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import requests
import ipaddress
import threading
import re
import json
import os
import configparser
from collections import Counter
from bs4 import BeautifulSoup

# ---------- IP RANGE MERGER LOGIC ----------
def text_ip_to_int(txt: str) -> int:
    res = 0
    for part in txt.split('.'):
        res = (res * 256) + int(part)
    return res

def int_to_ip(ip_int: int) -> str:
    return f"{(ip_int >> 24) & 0xff}.{(ip_int >> 16) & 0xff}.{(ip_int >> 8) & 0xff}.{ip_int & 0xff}"

def cidr_to_range(cidr: str):
    try:
        network = ipaddress.ip_network(cidr, strict=False)
        return {'from': int(network.network_address), 'to': int(network.broadcast_address) + 1}
    except:
        return None

def parse_to_range(entry: str):
    entry = entry.strip()
    m = re.match(r'(\d+\.\d+\.\d+\.\d+)/(\d+)', entry)
    if m:
        return cidr_to_range(entry)
    m = re.match(r'(\d+\.\d+\.\d+\.\d+)\s*-\s*(\d+\.\d+\.\d+\.\d+)', entry)
    if m:
        return {'from': text_ip_to_int(m.group(1)), 'to': text_ip_to_int(m.group(2)) + 1}
    m = re.match(r'(\d+\.\d+\.\d+\.\d+)', entry)
    if m:
        ip = text_ip_to_int(m.group(1))
        return {'from': ip, 'to': ip + 1}
    return None

def merge_ranges(ranges):
    if not ranges: return []
    ranges.sort(key=lambda x: (x['from'], x['to']))
    merged = []
    current = ranges[0].copy()
    for r in ranges[1:]:
        if r['from'] <= current['to']:
            current['to'] = max(current['to'], r['to'])
        else:
            merged.append(current)
            current = r.copy()
    merged.append(current)
    return merged

def ranges_to_cidrs(ranges):
    cidrs = []
    for rng in ranges:
        start = rng['from']
        end = rng['to']
        while start < end:
            size = 1
            while (start & (size - 1)) == 0 and (start + size) <= end:
                size <<= 1
            size >>= 1
            if size < 1: size = 1
            prefix_len = 32
            temp = size
            while temp > 1:
                temp >>= 1
                prefix_len -= 1
            cidrs.append(f"{int_to_ip(start)}/{prefix_len}")
            start += size
    return cidrs

def ranges_to_text(ranges):
    lines = []
    for rng in ranges:
        if rng['to'] == rng['from'] + 1:
            lines.append(int_to_ip(rng['from']))
        else:
            lines.append(f"{int_to_ip(rng['from'])}-{int_to_ip(rng['to'] - 1)}")
    return lines

def merge_and_format(input_text: str, output_type: str):
    if not input_text or not input_text.strip():
        return []
    raw_items = re.split(r'[,\n\r\t\|]+', input_text)
    ranges = []
    for item in raw_items:
        item = item.strip()
        if not item: continue
        rng = parse_to_range(item)
        if rng: ranges.append(rng)
    if not ranges: return []
    merged = merge_ranges(ranges)
    if output_type == "cidr":
        return ranges_to_cidrs(merged)
    else:
        return ranges_to_text(merged)

# ---------- СПИСОК СТРАН ----------
COUNTRIES_LIST = [
    ("Афганистан", "afghanistan"), ("Аландские острова", "aland-islands"),
    ("Албания", "albania"), ("Алжир", "algeria"), ("Американское Самоа", "american-samoa"),
    ("Андорра", "andorra"), ("Ангола", "angola"), ("Ангуилла", "anguilla"),
    ("Антарктика", "antarctica"), ("Антигуа и Барбуда", "antigua-and-barbuda"),
    ("Аргентина", "argentina"), ("Армения", "armenia"), ("Аруба", "aruba"),
    ("Австралия", "australia"), ("Австрия", "austria"), ("Азербайджан", "azerbaijan"),
    ("Багамские острова", "bahamas"), ("Бахрейн", "bahrain"), ("Бангладеш", "bangladesh"),
    ("Барбадос", "barbados"), ("Беларусь", "belarus"), ("Бельгия", "belgium"),
    ("Белиз", "belize"), ("Бенин", "benin"), ("Бермудские Острова", "bermuda"),
    ("Бутан", "bhutan"), ("Боливия", "bolivia-plurinational-state-of"),
    ("Бонайре, Синт-Эстатиус и Саба", "bonaire-sint-eustatius-and-saba"),
    ("Босния и Герцеговина", "bosnia-and-herzegovina"), ("Ботсвана", "botswana"),
    ("Бразилия", "brazil"), ("Бруней Даруссалам", "brunei-darussalam"), ("Болгария", "bulgaria"),
    ("Буркина Фасо", "burkina-faso"), ("Бурунди", "burundi"), ("Камбоджа", "cambodia"),
    ("Камерун", "cameroon"), ("Канада", "canada"), ("Каймановы острова", "cayman-islands"),
    ("Чад", "chad"), ("Чили", "chile"), ("Китай", "china"), ("Колумбия", "colombia"),
    ("Коморские Острова", "comoros"), ("Конго", "congo"), ("Коста-Рика", "costa-rica"),
    ("Хорватия", "croatia"), ("Куба", "cuba"), ("Кюрасао", "curacao"), ("Кипр", "cyprus"),
    ("Чешская республика", "czechia"), ("Дания", "denmark"), ("Джибути", "djibouti"),
    ("Доминиканская Республика", "dominican-republic"), ("Эквадор", "ecuador"),
    ("Египет", "egypt"), ("Сальвадор", "el-salvador"), ("Эритрея", "eritrea"),
    ("Эстония", "estonia"), ("Эфиопия", "ethiopia"), ("Фиджи", "fiji"),
    ("Финляндия", "finland"), ("Франция", "france"), ("Габон", "gabon"), ("Гамбия", "gambia"),
    ("Грузия", "georgia"), ("Германия", "germany"), ("Гана", "ghana"), ("Греция", "greece"),
    ("Гренландия", "greenland"), ("Гренада", "grenada"), ("Гваделупа", "guadeloupe"),
    ("Гуам", "guam"), ("Гватемала", "guatemala"), ("Гвинея", "guinea"),
    ("Гвинея-Биссау", "guinea-bissau"), ("Гайана", "guyana"), ("Гаити", "haiti"),
    ("Ватикан", "holy-see"), ("Гондурас", "honduras"), ("Гонконг", "hong-kong"),
    ("Венгрия", "hungary"), ("Исландия", "iceland"), ("Индия", "india"),
    ("Индонезия", "indonesia"), ("Иран", "iran-islamic-republic-of"), ("Ирак", "iraq"),
    ("Ирландия", "ireland"), ("Израиль", "israel"), ("Италия", "italy"), ("Ямайка", "jamaica"),
    ("Япония", "japan"), ("Иордания", "jordan"), ("Казахстан", "kazakhstan"),
    ("Кения", "kenya"), ("Кирибати", "kiribati"), ("Кувейт", "kuwait"),
    ("Кыргызстан", "kyrgyzstan"), ("Лаос", "lao-peoples-democratic-republic"),
    ("Латвия", "latvia"), ("Ливан", "lebanon"), ("Либерия", "liberia"), ("Ливия", "libya"),
    ("Лихтенштейн", "liechtenstein"), ("Литва", "lithuania"), ("Люксембург", "luxembourg"),
    ("Мадагаскар", "madagascar"), ("Малави", "malawi"), ("Малайзия", "malaysia"),
    ("Мальдивы", "maldives"), ("Мали", "mali"), ("Мальта", "malta"),
    ("Маршалловы Острова", "marshall-islands"), ("Мавритания", "mauritania"),
    ("Маврикий", "mauritius"), ("Мексика", "mexico"), ("Молдова", "moldova-republic-of"),
    ("Монако", "monaco"), ("Монголия", "mongolia"), ("Черногория", "montenegro"),
    ("Марокко", "morocco"), ("Мозамбик", "mozambique"), ("Мьянма", "myanmar"),
    ("Намибия", "namibia"), ("Науру", "nauru"), ("Непал", "nepal"), ("Нидерланды", "netherlands"),
    ("Новая Зеландия", "new-zealand"), ("Никарагуа", "nicaragua"), ("Нигер", "niger"),
    ("Нигерия", "nigeria"), ("Северная Корея", "korea-democratic-peoples-republic-of"),
    ("Северная Македония", "north-macedonia"), ("Норвегия", "norway"), ("Оман", "oman"),
    ("Пакистан", "pakistan"), ("Палау", "palau"), ("Панама", "panama"),
    ("Папуа-Новая Гвинея", "papua-new-guinea"), ("Парагвай", "paraguay"), ("Перу", "peru"),
    ("Филиппины", "philippines"), ("Польша", "poland"), ("Португалия", "portugal"),
    ("Пуэрто-Рико", "puerto-rico"), ("Катар", "qatar"), ("Румыния", "romania"),
    ("Россия", "russian-federation"), ("Руанда", "rwanda"), ("Самоа", "samoa"),
    ("Сан-Марино", "san-marino"), ("Саудовская Аравия", "saudi-arabia"), ("Сенегал", "senegal"),
    ("Сербия", "serbia"), ("Сейшельские Острова", "seychelles"), ("Сьерра-Леоне", "sierra-leone"),
    ("Сингапур", "singapore"), ("Словакия", "slovakia"), ("Словения", "slovenia"),
    ("Соломоновы Острова", "solomon-islands"), ("Сомали", "somalia"), ("Южная Африка", "south-africa"),
    ("Южная Корея", "korea-republic-of"), ("Южный Судан", "south-sudan"), ("Испания", "spain"),
    ("Шри-Ланка", "sri-lanka"), ("Судан", "sudan"), ("Суринам", "suriname"), ("Швеция", "sweden"),
    ("Швейцария", "switzerland"), ("Сирия", "syrian-arab-republic"), ("Тайвань", "taiwan-province-of-china"),
    ("Таджикистан", "tajikistan"), ("Танзания", "tanzania-united-republic-of"), ("Таиланд", "thailand"),
    ("Тимор-Лесте", "timor-leste"), ("Того", "togo"), ("Тонга", "tonga"),
    ("Тринидад и Тобаго", "trinidad-and-tobago"), ("Тунис", "tunisia"), ("Турция", "turkey"),
    ("Туркменистан", "turkmenistan"), ("Тувалу", "tuvalu"), ("Уганда", "uganda"), ("Украина", "ukraine"),
    ("ОАЭ", "united-arab-emirates"), ("Великобритания", "united-kingdom-of-great-britain-and-northern-ireland"),
    ("США", "united-states-of-america"), ("Уругвай", "uruguay"), ("Узбекистан", "uzbekistan"),
    ("Вануату", "vanuatu"), ("Венесуэла", "venezuela-(bolivarian-republic-of)"), ("Вьетнам", "viet-nam"),
    ("Йемен", "yemen"), ("Замбия", "zambia"), ("Зимбабве", "zimbabwe"),
]

# ---------- ФУНКЦИЯ ПОЛУЧЕНИЯ IP ДИАПАЗОНОВ ----------
def get_json_url_from_country_page(country_id: str, lang: str = 'ru'):
    """Загружает страницу страны и находит ссылку на JSON с диапазонами"""
    if lang == 'ru':
        url = f"https://lite.ip2location.com/ru/{country_id}-ip-address-ranges"
    else:
        url = f"https://lite.ip2location.com/{country_id}-ip-address-ranges"
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        json_pattern = r'https://cdn-lite\.ip2location\.com/datasets/([A-Z]{2})\.json'
        match = re.search(json_pattern, response.text)
        
        if match:
            return f"https://cdn-lite.ip2location.com/datasets/{match.group(1)}.json"
        
        alt_pattern = r'(https://[^\s"\']+\.json)'
        alt_match = re.search(alt_pattern, response.text)
        if alt_match:
            return alt_match.group(1)
        
        return None
    except Exception as e:
        print(f"Ошибка загрузки страницы {country_id}: {e}")
        return None

def fetch_ranges_from_json(json_url: str):
    """Скачивает JSON и извлекает IP диапазоны"""
    try:
        response = requests.get(json_url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        ranges = []
        if 'data' in data and isinstance(data['data'], list):
            for item in data['data']:
                if len(item) >= 2:
                    ranges.append(f"{item[0]}-{item[1]}")
        return ranges
    except Exception as e:
        print(f"Ошибка загрузки JSON {json_url}: {e}")
        return []

def fetch_country_ranges(country_id: str, lang: str = 'ru'):
    """Получает диапазоны для страны по её ID"""
    json_url = get_json_url_from_country_page(country_id, lang)
    if json_url:
        return fetch_ranges_from_json(json_url)
    return []

# ---------- GUI ПРИЛОЖЕНИЕ ----------
class CIDRMergerApp:
    def __init__(self, root):
        self.root = root
        root.title("CIDR Merger & IP Range Parser (IP2Location)")
        
        # Загрузка настроек
        self.config_file = "ip_merger_settings.ini"
        self.load_settings()
        
        # Данные для статистики
        self.country_stats = Counter()
        
        # Оптимальный размер для большинства экранов
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        window_width = min(self.settings.get('window_width', 1300), screen_width - 50)
        window_height = min(self.settings.get('window_height', 800), screen_height - 50)
        
        # Проверяем, что x и y не None
        x = self.settings.get('window_x')
        y = self.settings.get('window_y')
        
        if x is None or y is None:
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
        
        root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        root.minsize(1000, 600)
        
        # Привязка события закрытия
        root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.countries_data = COUNTRIES_LIST
        self.filtered_countries = COUNTRIES_LIST
        self.current_lang = self.settings.get('language', 'ru')

        self.create_widgets()
        self.setup_hotkeys()
        self.setup_context_menus()
        
        self.update_country_list()
        self.update_left_frame_title()

    def load_settings(self):
        """Загрузка настроек из INI файла"""
        self.settings = {
            'window_width': 1300,
            'window_height': 800,
            'window_x': None,
            'window_y': None,
            'language': 'ru',
            'auto_clear': True,
            'paned_position': 350
        }
        
        if os.path.exists(self.config_file):
            try:
                config = configparser.ConfigParser()
                config.read(self.config_file, encoding='utf-8')
                
                if 'Window' in config:
                    self.settings['window_width'] = config.getint('Window', 'width', fallback=1300)
                    self.settings['window_height'] = config.getint('Window', 'height', fallback=800)
                    # Читаем x и y, если они есть
                    x_val = config.get('Window', 'x', fallback=None)
                    y_val = config.get('Window', 'y', fallback=None)
                    if x_val and x_val != 'None':
                        self.settings['window_x'] = int(x_val)
                    if y_val and y_val != 'None':
                        self.settings['window_y'] = int(y_val)
                
                if 'Settings' in config:
                    self.settings['language'] = config.get('Settings', 'language', fallback='ru')
                    self.settings['auto_clear'] = config.getboolean('Settings', 'auto_clear', fallback=True)
                    self.settings['paned_position'] = config.getint('Settings', 'paned_position', fallback=350)
            except Exception as e:
                print(f"Ошибка загрузки настроек: {e}")
                pass

    def save_settings(self):
        """Сохранение настроек в INI файл"""
        try:
            config = configparser.ConfigParser()
            
            # Получаем текущую геометрию окна
            geometry = self.root.geometry()
            match = re.match(r'(\d+)x(\d+)\+(-?\d+)\+(-?\d+)', geometry)
            if match:
                width, height, x, y = map(int, match.groups())
                config['Window'] = {
                    'width': str(width),
                    'height': str(height),
                    'x': str(x),
                    'y': str(y)
                }
            
            # Сохраняем настройки
            config['Settings'] = {
                'language': self.current_lang,
                'auto_clear': str(self.auto_clear_var.get()),
                'paned_position': str(self.main_paned.sashpos(0) if hasattr(self, 'main_paned') else 350)
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                config.write(f)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
            pass

    def on_closing(self):
        """Обработка закрытия окна"""
        self.save_settings()
        self.root.destroy()

    def update_left_frame_title(self):
        """Обновляет заголовок левого поля с отображением статистики"""
        if hasattr(self, 'left_output_frame'):
            if self.country_stats:
                stats_str = ", ".join([f"{country} {count} стр" for country, count in self.country_stats.most_common(3)])
                title = f"📋 IP-диапазоны ({stats_str})"
            else:
                title = "📋 IP-диапазоны (пусто)"
            self.left_output_frame.config(text=title)

    def add_to_stats(self, country_name, ranges_count):
        """Добавляет статистику по стране"""
        if ranges_count > 0:
            self.country_stats[country_name] += ranges_count
            self.update_left_frame_title()

    def clear_stats(self):
        """Очищает статистику"""
        self.country_stats.clear()
        self.update_left_frame_title()

    def create_widgets(self):
        # Основной контейнер с разделением
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # ЛЕВАЯ ПАНЕЛЬ
        left_panel = ttk.Frame(self.main_paned)
        self.main_paned.add(left_panel, weight=35)
        
        # ПРАВАЯ ПАНЕЛЬ
        right_panel = ttk.Frame(self.main_paned)
        self.main_paned.add(right_panel, weight=65)
        
        # Устанавливаем сохраненную позицию разделителя
        self.root.update_idletasks()
        self.main_paned.sashpos(0, self.settings.get('paned_position', 350))
        
        # ========== ЛЕВАЯ ПАНЕЛЬ ==========
        search_frame = ttk.LabelFrame(left_panel, text="🔍 Поиск страны", padding=5)
        search_frame.pack(fill='x', pady=(0, 5))
        
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(fill='x', padx=5, pady=2)
        self.search_entry.bind('<KeyRelease>', self.on_search)
        
        search_buttons = ttk.Frame(search_frame)
        search_buttons.pack(fill='x', padx=5, pady=2)
        ttk.Button(search_buttons, text="Сброс", command=self.clear_search).pack(side='left', padx=2)
        ttk.Label(search_buttons, text=f"Всего: {len(self.countries_data)}", font=('Arial', 8)).pack(side='right', padx=2)
        
        list_frame = ttk.LabelFrame(left_panel, text="📋 Выберите страны", padding=5)
        list_frame.pack(fill='both', expand=True)
        
        listbox_container = ttk.Frame(list_frame)
        listbox_container.pack(fill='both', expand=True)
        
        scroll_y = ttk.Scrollbar(listbox_container)
        scroll_y.pack(side='right', fill='y')
        scroll_x = ttk.Scrollbar(listbox_container, orient='horizontal')
        scroll_x.pack(side='bottom', fill='x')
        
        self.country_listbox = tk.Listbox(listbox_container, selectmode='extended',
                                          yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set,
                                          font=('Arial', 9), exportselection=False)
        self.country_listbox.pack(side='left', fill='both', expand=True)
        scroll_y.config(command=self.country_listbox.yview)
        scroll_x.config(command=self.country_listbox.xview)
        
        select_buttons = ttk.Frame(list_frame)
        select_buttons.pack(fill='x', pady=5)
        ttk.Button(select_buttons, text="Выбрать все", command=self.select_all_countries).pack(side='left', padx=2)
        ttk.Button(select_buttons, text="Снять выбор", command=self.deselect_all_countries).pack(side='left', padx=2)
        
        self.load_btn = ttk.Button(list_frame, text="🚀 Загрузить IP-диапазоны", 
                                   command=self.load_selected_ranges)
        self.load_btn.pack(fill='x', pady=5)
        
        settings_frame = ttk.LabelFrame(left_panel, text="⚙️ Настройки", padding=5)
        settings_frame.pack(fill='x', pady=(5, 0))
        
        lang_frame = ttk.Frame(settings_frame)
        lang_frame.pack(fill='x', pady=2)
        ttk.Label(lang_frame, text="Версия сайта:").pack(side='left')
        self.lang_var = tk.StringVar(value=self.current_lang)
        ttk.Radiobutton(lang_frame, text="Рус", variable=self.lang_var, value="ru", 
                        command=self.on_lang_change).pack(side='left', padx=5)
        ttk.Radiobutton(lang_frame, text="Eng", variable=self.lang_var, value="en", 
                        command=self.on_lang_change).pack(side='left', padx=5)
        
        self.auto_clear_var = tk.BooleanVar(value=self.settings.get('auto_clear', True))
        ttk.Checkbutton(settings_frame, text="Автоочистка перед загрузкой", 
                        variable=self.auto_clear_var).pack(anchor='w', pady=2)
        
        self.status_label = ttk.Label(left_panel, text="✅ Готов", font=('Arial', 8), foreground="green")
        self.status_label.pack(fill='x', pady=(5, 0))
        
        # ========== ПРАВАЯ ПАНЕЛЬ ==========
        control_frame = ttk.Frame(right_panel)
        control_frame.pack(fill='x', pady=(0, 5))
        
        ttk.Button(control_frame, text="🗑 Очистить всё", command=self.clear_all_output, 
                   width=12).pack(side='left', padx=2)
        ttk.Button(control_frame, text="Очистить левое", 
                   command=lambda: self.clear_text(self.left_text)).pack(side='left', padx=2)
        ttk.Button(control_frame, text="Очистить правое", 
                   command=lambda: self.clear_text(self.right_text)).pack(side='left', padx=2)
        ttk.Button(control_frame, text="Сбросить статистику", 
                   command=self.clear_stats).pack(side='left', padx=2)
        
        output_paned = ttk.PanedWindow(right_panel, orient=tk.HORIZONTAL)
        output_paned.pack(fill=tk.BOTH, expand=True)
        
        # Левое окно (диапазоны)
        self.left_output_frame = ttk.LabelFrame(output_paned, text="📋 IP-диапазоны (пусто)", padding=5)
        output_paned.add(self.left_output_frame, weight=50)
        
        self.left_text = scrolledtext.ScrolledText(self.left_output_frame, wrap=tk.NONE, 
                                                    font=('Courier', 9), undo=True)
        self.left_text.pack(fill='both', expand=True)
        
        left_btns = ttk.Frame(self.left_output_frame)
        left_btns.pack(fill='x', pady=5)
        ttk.Button(left_btns, text="📂 Импорт", command=lambda: self.import_file(self.left_text), 
                   width=9).pack(side='left', padx=2)
        ttk.Button(left_btns, text="💾 Экспорт", command=lambda: self.export_file(self.left_text), 
                   width=9).pack(side='left', padx=2)
        ttk.Button(left_btns, text="🔄 Слияние", command=lambda: self.merge_text(self.left_text, "range"), 
                   width=9).pack(side='left', padx=2)
        ttk.Button(left_btns, text="→ В CIDR", command=self.convert_left_to_right, 
                   width=9).pack(side='left', padx=2)
        
        # Правое окно (CIDR)
        right_output_frame = ttk.LabelFrame(output_paned, text="🔗 CIDR (IP/маска)", padding=5)
        output_paned.add(right_output_frame, weight=50)
        
        self.right_text = scrolledtext.ScrolledText(right_output_frame, wrap=tk.NONE, 
                                                     font=('Courier', 9), undo=True)
        self.right_text.pack(fill='both', expand=True)
        
        right_btns = ttk.Frame(right_output_frame)
        right_btns.pack(fill='x', pady=5)
        ttk.Button(right_btns, text="📂 Импорт", command=lambda: self.import_file(self.right_text), 
                   width=9).pack(side='left', padx=2)
        ttk.Button(right_btns, text="💾 Экспорт", command=lambda: self.export_file(self.right_text), 
                   width=9).pack(side='left', padx=2)
        ttk.Button(right_btns, text="🔄 Слияние", command=lambda: self.merge_text(self.right_text, "cidr"), 
                   width=9).pack(side='left', padx=2)
        ttk.Button(right_btns, text="← В диапазоны", command=self.convert_right_to_left, 
                   width=10).pack(side='left', padx=2)

    def on_lang_change(self):
        self.current_lang = self.lang_var.get()
        self.save_settings()
        self.status_label.config(text=f"🌐 Язык: {'Русский' if self.current_lang == 'ru' else 'English'}", 
                                 foreground="blue")
        self.root.after(2000, lambda: self.status_label.config(text="✅ Готов", foreground="green"))

    def clear_search(self):
        self.search_entry.delete(0, tk.END)
        self.on_search(None)

    def update_country_list(self):
        self.country_listbox.delete(0, tk.END)
        for name, country_id in self.filtered_countries:
            self.country_listbox.insert(tk.END, f"{name}")
        self.status_label.config(text=f"✅ Загружено {len(self.filtered_countries)} стран", 
                                 foreground="green")

    def on_search(self, event):
        query = self.search_entry.get().strip().lower()
        if not query:
            self.filtered_countries = self.countries_data
        else:
            self.filtered_countries = [(n, c) for n, c in self.countries_data if query in n.lower()]
        self.update_country_list()

    def select_all_countries(self):
        self.country_listbox.select_set(0, tk.END)
        
    def deselect_all_countries(self):
        self.country_listbox.select_clear(0, tk.END)

    def clear_text(self, text_widget):
        text_widget.delete("1.0", tk.END)
        self.status_label.config(text="🗑 Очищено", foreground="blue")
        self.root.after(1500, lambda: self.status_label.config(text="✅ Готов", foreground="green"))
        
    def clear_all_output(self):
        self.left_text.delete("1.0", tk.END)
        self.right_text.delete("1.0", tk.END)
        self.clear_stats()
        self.status_label.config(text="🗑 Весь вывод очищен", foreground="blue")
        self.root.after(1500, lambda: self.status_label.config(text="✅ Готов", foreground="green"))

    def setup_hotkeys(self):
        self.root.bind('<Control-c>', lambda e: self.copy_focused())
        self.root.bind('<Control-v>', lambda e: self.paste_focused())
        self.root.bind('<Control-a>', lambda e: self.select_all_focused())
        self.root.bind('<Control-x>', lambda e: self.cut_focused())

    def setup_context_menus(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="✂ Вырезать", command=self.cut_focused)
        self.context_menu.add_command(label="📋 Копировать", command=self.copy_focused)
        self.context_menu.add_command(label="📎 Вставить", command=self.paste_focused)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🔲 Выделить всё", command=self.select_all_focused)

        def show(event):
            w = event.widget
            if isinstance(w, (tk.Text, scrolledtext.ScrolledText)):
                try:
                    if w.selection_get():
                        self.context_menu.entryconfig("✂ Вырезать", state="normal")
                        self.context_menu.entryconfig("📋 Копировать", state="normal")
                    else:
                        self.context_menu.entryconfig("✂ Вырезать", state="disabled")
                        self.context_menu.entryconfig("📋 Копировать", state="disabled")
                except:
                    self.context_menu.entryconfig("✂ Вырезать", state="disabled")
                    self.context_menu.entryconfig("📋 Копировать", state="disabled")
                self.context_menu.post(event.x_root, event.y_root)
        self.root.bind('<Button-3>', show)

    def get_focused_text(self):
        w = self.root.focus_get()
        if isinstance(w, (tk.Text, scrolledtext.ScrolledText)):
            return w
        return None

    def copy_focused(self):
        w = self.get_focused_text()
        if w:
            try:
                sel = w.selection_get()
                self.root.clipboard_clear()
                self.root.clipboard_append(sel)
                self.status_label.config(text="✅ Скопировано", foreground="blue")
                self.root.after(1500, lambda: self.status_label.config(text="✅ Готов", foreground="green"))
            except: pass

    def cut_focused(self):
        w = self.get_focused_text()
        if w:
            try:
                sel = w.selection_get()
                self.root.clipboard_clear()
                self.root.clipboard_append(sel)
                w.delete(tk.SEL_FIRST, tk.SEL_LAST)
                self.status_label.config(text="✂ Вырезано", foreground="blue")
                self.root.after(1500, lambda: self.status_label.config(text="✅ Готов", foreground="green"))
            except: pass

    def paste_focused(self):
        w = self.get_focused_text()
        if w:
            try:
                text = self.root.clipboard_get()
                w.insert(tk.INSERT, text)
                self.status_label.config(text="📎 Вставлено", foreground="blue")
                self.root.after(1500, lambda: self.status_label.config(text="✅ Готов", foreground="green"))
            except: pass

    def select_all_focused(self):
        w = self.get_focused_text()
        if w:
            w.tag_add(tk.SEL, "1.0", tk.END)
            w.mark_set(tk.INSERT, "1.0")
            w.see(tk.INSERT)

    def load_selected_ranges(self):
        sel = self.country_listbox.curselection()
        if not sel:
            messagebox.showinfo("Информация", "Пожалуйста, выберите хотя бы одну страну")
            return
        
        if self.auto_clear_var.get():
            self.left_text.delete("1.0", tk.END)
            self.right_text.delete("1.0", tk.END)
            self.clear_stats()
        
        self.status_label.config(text="⏳ Загрузка диапазонов...", foreground="orange")
        self.load_btn.config(state='disabled', text="⏳ Загрузка...")
        self.root.update()
        
        all_ranges = []
        failed_countries = []
        
        for idx in sel:
            name, country_id = self.filtered_countries[idx]
            self.status_label.config(text=f"⏳ Загрузка: {name}...", foreground="orange")
            self.root.update()
            
            ranges = fetch_country_ranges(country_id, self.current_lang)
            
            if ranges:
                all_ranges.extend(ranges)
                self.add_to_stats(name, len(ranges))
                self.status_label.config(text=f"✅ {name}: {len(ranges)} диапазонов", foreground="green")
            else:
                failed_countries.append(name)
                self.status_label.config(text=f"⚠️ {name}: диапазоны не найдены", foreground="red")
            
            self.root.update()
        
        if all_ranges:
            current = self.left_text.get("1.0", tk.END).strip()
            new_content = "\n".join(all_ranges)
            if current and not self.auto_clear_var.get():
                new_content = current + "\n" + new_content
            self.left_text.delete("1.0", tk.END)
            self.left_text.insert("1.0", new_content)
            
            self.merge_text(self.left_text, "range")
            
            status_msg = f"✅ Загружено {len(all_ranges)} диапазонов"
            if failed_countries:
                status_msg += f" (не загружено: {', '.join(failed_countries[:3])})"
            self.status_label.config(text=status_msg, foreground="green")
        else:
            self.status_label.config(text="❌ Диапазоны не найдены ни для одной страны", foreground="red")
            messagebox.showwarning("Нет данных", "Не удалось найти IP диапазоны для выбранных стран")
        
        self.load_btn.config(state='normal', text="🚀 Загрузить IP-диапазоны")

    def merge_text(self, text_widget, target_type):
        content = text_widget.get("1.0", tk.END).strip()
        if not content:
            messagebox.showinfo("Информация", "Нет данных для обработки")
            return
        
        self.status_label.config(text="🔄 Выполняется слияние...", foreground="orange")
        self.root.update()
        
        result = merge_and_format(content, target_type)
        
        if result:
            text_widget.delete("1.0", tk.END)
            text_widget.insert("1.0", "\n".join(result))
            self.status_label.config(text=f"✅ Слияние: {len(result)} записей", foreground="green")
            self.root.after(2000, lambda: self.status_label.config(text="✅ Готов", foreground="green"))
        else:
            self.status_label.config(text="❌ Ошибка слияния", foreground="red")

    def convert_left_to_right(self):
        content = self.left_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showinfo("Информация", "Нет данных для конвертации")
            return
        
        self.status_label.config(text="🔄 Конвертация в CIDR...", foreground="orange")
        self.root.update()
        
        cidrs = merge_and_format(content, "cidr")
        
        if cidrs:
            self.right_text.delete("1.0", tk.END)
            self.right_text.insert("1.0", "\n".join(cidrs))
            self.status_label.config(text=f"✅ Сконвертировано {len(cidrs)} CIDR", foreground="green")
            self.root.after(2000, lambda: self.status_label.config(text="✅ Готов", foreground="green"))
        else:
            self.status_label.config(text="❌ Ошибка конвертации", foreground="red")

    def convert_right_to_left(self):
        content = self.right_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showinfo("Информация", "Нет данных для конвертации")
            return
        
        self.status_label.config(text="🔄 Конвертация в диапазоны...", foreground="orange")
        self.root.update()
        
        ranges = merge_and_format(content, "range")
        
        if ranges:
            self.left_text.delete("1.0", tk.END)
            self.left_text.insert("1.0", "\n".join(ranges))
            self.status_label.config(text=f"✅ Сконвертировано {len(ranges)} диапазонов", foreground="green")
            self.root.after(2000, lambda: self.status_label.config(text="✅ Готов", foreground="green"))
        else:
            self.status_label.config(text="❌ Ошибка конвертации", foreground="red")

    def import_file(self, text_widget):
        fname = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if fname:
            try:
                with open(fname, 'r', encoding='utf-8') as f:
                    data = f.read()
                text_widget.delete("1.0", tk.END)
                text_widget.insert("1.0", data)
                self.status_label.config(text="✅ Импорт выполнен", foreground="green")
                self.root.after(2000, lambda: self.status_label.config(text="✅ Готов", foreground="green"))
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось импортировать: {e}")

    def export_file(self, text_widget):
        fname = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if fname:
            try:
                data = text_widget.get("1.0", tk.END).strip()
                if not data:
                    messagebox.showwarning("Предупреждение", "Нет данных для экспорта")
                    return
                with open(fname, 'w', encoding='utf-8') as f:
                    f.write(data)
                self.status_label.config(text="✅ Экспорт выполнен", foreground="green")
                self.root.after(2000, lambda: self.status_label.config(text="✅ Готов", foreground="green"))
                messagebox.showinfo("Успех", "Данные экспортированы")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось экспортировать: {e}")

# ---------- ЗАПУСК ----------
if __name__ == "__main__":
    root = tk.Tk()
    app = CIDRMergerApp(root)
    root.mainloop()
