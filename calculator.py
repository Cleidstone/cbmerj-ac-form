import math

# Fatores de cálculo extraídos da planilha BM4 "CARGA TÉRMICA Modelo.xlsx"
ROOM_TYPE_FACTORS = {
    'standard': {
        'area': 270.75, 'people': 270.75, 'appliances': 270.75,
        'lamps': 15.39, 'window_morning': 270.75, 'window_afternoon': 361,
        'label': 'Sala de aula / Escritório / Dormitório (padrão)',
    },
    'afternoon_sun': {
        'area': 500, 'people': 270.75, 'appliances': 270.75,
        'lamps': 15.39, 'window_morning': 270.75, 'window_afternoon': 361,
        'label': 'Sala com fachada exposta ao sol da tarde (oeste)',
    },
    'large': {
        'area': 600, 'people': 600, 'appliances': 600,
        'lamps': 34.1, 'window_morning': 600, 'window_afternoon': 800,
        'label': 'Refeitório / Auditório / Área de uso amplo',
    },
}

STANDARD_SIZES = [12000, 18000, 36000, 60000]

EMOP = {
    12000: {'supply': '18.030.0002-0', 'desc': 'Condicionador de ar tipo SPLIT 12.000 BTU/h'},
    18000: {'supply': '18.030.0003-0', 'desc': 'Condicionador de ar tipo SPLIT 18.000 BTU/h'},
    36000: {'supply': '18.030.0008-0', 'desc': 'Condicionador de ar tipo SPLIT 36.000 BTU/h'},
    60000: {'supply': '18.030.0010-0', 'desc': 'Condicionador de ar tipo SPLIT 60.000 BTU/h'},
}

INSTALL_EMOP = {
    'small': {'code': '15.005.0215-0', 'pipe': '15.005.0240-0',
              'desc': 'Assentamento Split 9.000 a 30.000 BTU/h',
              'pipe_desc': 'Tubulação cobre Split 9.000 a 30.000 BTU/h'},
    'large': {'code': '15.005.0220-0', 'pipe': '15.005.0245-0',
              'desc': 'Assentamento Split 36.000 a 60.000 BTU/h',
              'pipe_desc': 'Tubulação cobre Split 36.000 a 60.000 BTU/h'},
}


def calculate_btu(area, people, appliances, lamps, window_morning, window_afternoon, room_type='standard'):
    f = ROOM_TYPE_FACTORS.get(room_type, ROOM_TYPE_FACTORS['standard'])
    btu = (
        area * f['area'] +
        people * f['people'] +
        appliances * f['appliances'] +
        lamps * f['lamps'] +
        window_morning * f['window_morning'] +
        window_afternoon * f['window_afternoon']
    )
    return round(btu, 2)


def get_calculation_breakdown(area, people, appliances, lamps, window_morning, window_afternoon, room_type='standard'):
    f = ROOM_TYPE_FACTORS.get(room_type, ROOM_TYPE_FACTORS['standard'])
    return [
        ('Área do ambiente', f'{area:.2f} m²', f['area'], area * f['area']),
        ('Número de pessoas', people, f['people'], people * f['people']),
        ('Aparelhos eletrônicos', appliances, f['appliances'], appliances * f['appliances']),
        ('Lâmpadas de 10W', lamps, f['lamps'], lamps * f['lamps']),
        ('Janela - sol da manhã', window_morning, f['window_morning'], window_morning * f['window_morning']),
        ('Janela - sol da tarde', window_afternoon, f['window_afternoon'], window_afternoon * f['window_afternoon']),
    ]


def recommend_ac(btu_needed):
    for size in STANDARD_SIZES:
        if btu_needed <= size:
            return size, 1
    n = math.ceil(btu_needed / 60000)
    return 60000, n


def get_emop_codes(size):
    supply = EMOP.get(size, {'supply': 'N/A - verificar', 'desc': 'Tamanho não padronizado'})
    install_key = 'small' if size <= 30000 else 'large'
    install = INSTALL_EMOP[install_key]
    return {
        'supply_code': supply['supply'],
        'supply_desc': supply['desc'],
        'install_code': install['code'],
        'install_desc': install['desc'],
        'pipe_code': install['pipe'],
        'pipe_desc': install['pipe_desc'],
    }


def format_btu(value):
    return f"{value:,.0f}".replace(',', '.')
