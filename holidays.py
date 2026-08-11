# holidays.py
# -*- coding: utf-8 -*-
"""
Data hari libur nasional, keagamaan, internasional
Dengan terjemahan ID/EN - API dinonaktifkan sementara untuk kecepatan startup.
"""

import requests
from datetime import datetime
import json
import os

# ---- DATA STATIS LIBUR NASIONAL INDONESIA (fallback) ----
STATIC_HOLIDAYS = {
    "id": {
        "01-01": ("Tahun Baru Masehi", "New Year's Day"),
        "05-01": ("Hari Buruh Internasional", "International Workers' Day"),
        "08-17": ("Hari Kemerdekaan RI", "Indonesian Independence Day"),
        "12-25": ("Hari Natal", "Christmas Day"),
        "05-02": ("Hari Pendidikan Nasional", "National Education Day"),
        "11-10": ("Hari Pahlawan", "Heroes' Day"),
        "04-21": ("Hari Kartini", "Kartini Day"),
        "05-20": ("Hari Kebangkitan Nasional", "National Awakening Day"),
        "06-01": ("Hari Lahir Pancasila", "Pancasila Day"),
        "07-01": ("Hari Bhayangkara", "Police Day"),
        "07-12": ("Hari Koperasi", "Cooperative Day"),
        "07-23": ("Hari Anak Nasional", "National Children's Day"),
        "08-14": ("Hari Pramuka", "Scout Day"),
        "09-09": ("Hari Olahraga Nasional", "National Sports Day"),
        "10-01": ("Hari Kesaktian Pancasila", "Pancasila Sanctity Day"),
        "10-28": ("Hari Sumpah Pemuda", "Youth Pledge Day"),
        "01-25": ("Hari Gizi Nasional", "National Nutrition Day"),
        "02-09": ("Hari Pers Nasional", "National Press Day"),
        "10-02": ("Hari Batik Nasional", "National Batik Day"),
        "11-20": ("Hari Anak Sedunia", "Universal Children's Day"),
        "12-01": ("Hari AIDS Sedunia", "World AIDS Day"),
        "12-22": ("Hari Ibu", "Mother's Day"),
    },
    "en": {
        "01-01": ("Tahun Baru Masehi", "New Year's Day"),
        "05-01": ("Hari Buruh Internasional", "International Workers' Day"),
        "08-17": ("Hari Kemerdekaan RI", "Indonesian Independence Day"),
        "12-25": ("Hari Natal", "Christmas Day"),
        "05-02": ("Hari Pendidikan Nasional", "National Education Day"),
        "11-10": ("Hari Pahlawan", "Heroes' Day"),
        "04-21": ("Hari Kartini", "Kartini Day"),
        "05-20": ("Hari Kebangkitan Nasional", "National Awakening Day"),
        "06-01": ("Hari Lahir Pancasila", "Pancasila Day"),
        "07-01": ("Hari Bhayangkara", "Police Day"),
        "07-12": ("Hari Koperasi", "Cooperative Day"),
        "07-23": ("Hari Anak Nasional", "National Children's Day"),
        "08-14": ("Hari Pramuka", "Scout Day"),
        "09-09": ("Hari Olahraga Nasional", "National Sports Day"),
        "10-01": ("Hari Kesaktian Pancasila", "Pancasila Sanctity Day"),
        "10-28": ("Hari Sumpah Pemuda", "Youth Pledge Day"),
        "01-25": ("Hari Gizi Nasional", "National Nutrition Day"),
        "02-09": ("Hari Pers Nasional", "National Press Day"),
        "10-02": ("Hari Batik Nasional", "National Batik Day"),
        "11-20": ("Hari Anak Sedunia", "Universal Children's Day"),
        "12-01": ("Hari AIDS Sedunia", "World AIDS Day"),
        "12-22": ("Hari Ibu", "Mother's Day"),
    }
}

# ---- DATA LIBUR KEAGAMAAN (per tahun) ----
RELIGIOUS_HOLIDAYS = {
    2025: {
        "03-31": ("Idul Fitri 1446 H", "Eid al-Fitr 1446 H"),
        "04-01": ("Idul Fitri 1446 H", "Eid al-Fitr 1446 H"),
        "04-02": ("Idul Fitri 1446 H", "Eid al-Fitr 1446 H"),
        "06-06": ("Idul Adha 1446 H", "Eid al-Adha 1446 H"),
        "06-27": ("Tahun Baru Islam 1447 H", "Islamic New Year 1447 H"),
        "09-05": ("Maulid Nabi Muhammad SAW", "Prophet Muhammad's Birthday"),
        "12-25": ("Hari Natal", "Christmas Day"),
        "12-26": ("Hari Natal", "Christmas Day"),
        "03-29": ("Hari Raya Nyepi 1947 Saka", "Nyepi Day 1947 Saka"),
        "05-23": ("Waisak 2569 BE", "Vesak Day 2569 BE"),
    },
    2026: {
        "03-21": ("Idul Fitri 1447 H", "Eid al-Fitr 1447 H"),
        "03-22": ("Idul Fitri 1447 H", "Eid al-Fitr 1447 H"),
        "03-23": ("Idul Fitri 1447 H", "Eid al-Fitr 1447 H"),
        "05-28": ("Idul Adha 1447 H", "Eid al-Adha 1447 H"),
        "06-17": ("Tahun Baru Islam 1448 H", "Islamic New Year 1448 H"),
        "08-26": ("Maulid Nabi Muhammad SAW", "Prophet Muhammad's Birthday"),
        "12-25": ("Hari Natal", "Christmas Day"),
        "12-26": ("Hari Natal", "Christmas Day"),
        "03-19": ("Hari Raya Nyepi 1948 Saka", "Nyepi Day 1948 Saka"),
        "05-13": ("Waisak 2570 BE", "Vesak Day 2570 BE"),
    },
    2027: {
        "03-10": ("Idul Fitri 1448 H", "Eid al-Fitr 1448 H"),
        "03-11": ("Idul Fitri 1448 H", "Eid al-Fitr 1448 H"),
        "03-12": ("Idul Fitri 1448 H", "Eid al-Fitr 1448 H"),
        "05-17": ("Idul Adha 1448 H", "Eid al-Adha 1448 H"),
        "06-06": ("Tahun Baru Islam 1449 H", "Islamic New Year 1449 H"),
        "08-16": ("Maulid Nabi Muhammad SAW", "Prophet Muhammad's Birthday"),
        "12-25": ("Hari Natal", "Christmas Day"),
        "12-26": ("Hari Natal", "Christmas Day"),
        "03-08": ("Hari Raya Nyepi 1949 Saka", "Nyepi Day 1949 Saka"),
        "05-02": ("Waisak 2571 BE", "Vesak Day 2571 BE"),
    },
    2028: {
        "02-28": ("Idul Fitri 1449 H", "Eid al-Fitr 1449 H"),
        "02-29": ("Idul Fitri 1449 H", "Eid al-Fitr 1449 H"),
        "03-01": ("Idul Fitri 1449 H", "Eid al-Fitr 1449 H"),
        "05-06": ("Idul Adha 1449 H", "Eid al-Adha 1449 H"),
        "05-26": ("Tahun Baru Islam 1450 H", "Islamic New Year 1450 H"),
        "08-05": ("Maulid Nabi Muhammad SAW", "Prophet Muhammad's Birthday"),
        "03-26": ("Hari Raya Nyepi 1950 Saka", "Nyepi Day 1950 Saka"),
        "05-10": ("Waisak 2572 BE", "Vesak Day 2572 BE"),
        "12-25": ("Hari Natal", "Christmas Day"),
    },
    2029: {
        # Catatan: tanggal keagamaan 2029 adalah PERKIRAAN (projeksi kalender
        # Hijriah/Saka). Verifikasi ke kalender resmi sebelum dipakai untuk keperluan penting.
        "02-17": ("Idul Fitri 1450 H", "Eid al-Fitr 1450 H"),
        "02-18": ("Idul Fitri 1450 H", "Eid al-Fitr 1450 H"),
        "02-19": ("Idul Fitri 1450 H", "Eid al-Fitr 1450 H"),
        "04-26": ("Idul Adha 1450 H", "Eid al-Adha 1450 H"),
        "05-16": ("Tahun Baru Islam 1451 H", "Islamic New Year 1451 H"),
        "07-26": ("Maulid Nabi Muhammad SAW", "Prophet Muhammad's Birthday"),
        "03-15": ("Hari Raya Nyepi 1951 Saka", "Nyepi Day 1951 Saka"),
        "05-28": ("Waisak 2573 BE", "Vesak Day 2573 BE"),
        "12-25": ("Hari Natal", "Christmas Day"),
        "12-26": ("Hari Natal", "Christmas Day"),
    },
}

# ---- HARI PERINGATAN INTERNASIONAL ----
INTERNATIONAL_DAYS = {
    "01-01": ("Tahun Baru Masehi", "New Year's Day"),
    "01-26": ("Hari Republik India", "Republic Day India"),
    "02-14": ("Hari Kasih Sayang", "Valentine's Day"),
    "03-08": ("Hari Perempuan Internasional", "International Women's Day"),
    "03-21": ("Hari Hutan Internasional", "International Forest Day"),
    "03-22": ("Hari Air Sedunia", "World Water Day"),
    "03-23": ("Hari Meteorologi Dunia", "World Meteorological Day"),
    "03-24": ("Hari TBC Sedunia", "World TB Day"),
    "04-07": ("Hari Kesehatan Sedunia", "World Health Day"),
    "04-22": ("Hari Bumi", "Earth Day"),
    "04-23": ("Hari Buku Sedunia", "World Book Day"),
    "04-25": ("Hari Malaria Sedunia", "World Malaria Day"),
    "05-01": ("Hari Buruh Internasional", "International Workers' Day"),
    "05-03": ("Hari Kebebasan Pers Sedunia", "World Press Freedom Day"),
    "05-08": ("Hari Palang Merah Sedunia", "World Red Cross Day"),
    "05-12": ("Hari Perawat Internasional", "International Nurses Day"),
    "05-17": ("Hari Telekomunikasi Sedunia", "World Telecommunication Day"),
    "05-20": ("Hari Lebah Sedunia", "World Bee Day"),
    "05-22": ("Hari Keanekaragaman Hayati", "Biodiversity Day"),
    "05-29": ("Hari Perdamaian", "International Day of UN Peacekeepers"),
    "05-31": ("Hari Tanpa Tembakau Sedunia", "World No Tobacco Day"),
    "06-01": ("Hari Anak Sedunia", "International Children's Day"),
    "06-05": ("Hari Lingkungan Hidup Sedunia", "World Environment Day"),
    "06-08": ("Hari Laut Sedunia", "World Oceans Day"),
    "06-14": ("Hari Donor Darah Sedunia", "World Blood Donor Day"),
    "06-20": ("Hari Pengungsi Sedunia", "World Refugee Day"),
    "06-23": ("Hari Pelayanan Publik PBB", "UN Public Service Day"),
    "06-26": ("Hari Anti Narkoba", "International Day Against Drug Abuse"),
    "07-11": ("Hari Populasi Sedunia", "World Population Day"),
    "07-28": ("Hari Hepatitis Sedunia", "World Hepatitis Day"),
    "08-09": ("Hari Masyarakat Adat Sedunia", "Indigenous Peoples Day"),
    "08-12": ("Hari Pemuda Internasional", "International Youth Day"),
    "08-19": ("Hari Kemanusiaan Sedunia", "World Humanitarian Day"),
    "09-08": ("Hari Aksara Sedunia", "International Literacy Day"),
    "09-16": ("Hari Ozon Sedunia", "Ozone Day"),
    "09-21": ("Hari Perdamaian Internasional", "International Peace Day"),
    "09-27": ("Hari Pariwisata Sedunia", "World Tourism Day"),
    "10-01": ("Hari Lansia Internasional", "International Day of Older Persons"),
    "10-02": ("Hari Non-Kekerasan Sedunia", "Non-Violence Day"),
    "10-05": ("Hari Guru Sedunia", "World Teachers' Day"),
    "10-09": ("Hari Pos Sedunia", "World Post Day"),
    "10-10": ("Hari Kesehatan Jiwa Sedunia", "World Mental Health Day"),
    "10-15": ("Hari Cuci Tangan Sedunia", "Global Handwashing Day"),
    "10-16": ("Hari Pangan Sedunia", "World Food Day"),
    "10-17": ("Hari Penghapusan Kemiskinan", "International Day for Eradication of Poverty"),
    "10-24": ("Hari PBB", "United Nations Day"),
    "10-27": ("Hari Warisan Audiovisual", "World Audiovisual Heritage Day"),
    "11-10": ("Hari Ilmu Pengetahuan", "World Science Day"),
    "11-14": ("Hari Diabetes Sedunia", "World Diabetes Day"),
    "11-16": ("Hari Toleransi Internasional", "International Tolerance Day"),
    "11-20": ("Hari Anak Sedunia", "Universal Children's Day"),
    "11-25": ("Hari Tanpa Kekerasan Terhadap Perempuan", "Elimination of Violence against Women"),
    "12-01": ("Hari AIDS Sedunia", "World AIDS Day"),
    "12-02": ("Hari Penghapusan Perbudakan", "Abolition of Slavery"),
    "12-03": ("Hari Penyandang Disabilitas", "International Day of Persons with Disabilities"),
    "12-05": ("Hari Sukarela Sedunia", "International Volunteer Day"),
    "12-07": ("Hari Penerbangan Sipil", "Civil Aviation Day"),
    "12-09": ("Hari Anti Korupsi Sedunia", "International Anti-Corruption Day"),
    "12-10": ("Hari Hak Asasi Manusia", "Human Rights Day"),
    "12-11": ("Hari Gunung Internasional", "International Mountain Day"),
    "12-18": ("Hari Migran Internasional", "International Migrants Day"),
    "01-27": ("Hari Peringatan Holocaust", "Holocaust Remembrance Day"),
    "02-04": ("Hari Kanker Sedunia", "World Cancer Day"),
    "02-20": ("Hari Keadilan Sosial", "Social Justice Day"),
    "03-01": ("Hari Nol Diskriminasi", "Zero Discrimination Day"),
    "03-03": ("Hari Satwa Liar Sedunia", "World Wildlife Day"),
    "03-15": ("Hari Hak Konsumen", "Consumer Rights Day"),
    "03-20": ("Hari Kebahagiaan Internasional", "International Happiness Day"),
    "04-02": ("Hari Autisme Sedunia", "World Autism Day"),
    "04-06": ("Hari Olahraga untuk Perdamaian", "Sport for Peace Day"),
    "05-05": ("Hari Kebersihan Tangan", "Hand Hygiene Day"),
    "05-15": ("Hari Keluarga Internasional", "International Family Day"),
    "05-18": ("Hari Museum Internasional", "International Museum Day"),
    "05-25": ("Hari Afrika", "Africa Day"),
    "06-03": ("Hari Sepeda Sedunia", "World Bicycle Day"),
    "06-12": ("Hari Anti Pekerja Anak", "Anti-Child Labour Day"),
    "06-21": ("Hari Yoga Internasional", "International Yoga Day"),
    "06-30": ("Hari Asteroid", "Asteroid Day"),
    "07-18": ("Hari Nelson Mandela", "Mandela Day"),
    "07-30": ("Hari Persahabatan Internasional", "Friendship Day"),
    "08-01": ("Hari Emansipasi", "Emancipation Day"),
    "08-23": ("Hari Penghapusan Perdagangan Budak", "Slave Trade Abolition Day"),
    "08-29": ("Hari Anti Uji Coba Nuklir", "Anti-Nuclear Test Day"),
    "09-05": ("Hari Amal", "Charity Day"),
    "09-12": ("Hari Kerjasama Selatan-Selatan", "South-South Cooperation Day"),
    "09-15": ("Hari Demokrasi Internasional", "International Democracy Day"),
    "09-23": ("Hari Bahasa Isyarat", "Sign Language Day"),
    "09-29": ("Hari Jantung Sedunia", "World Heart Day"),
    "10-04": ("Hari Hewan Sedunia", "World Animal Day"),
    "10-11": ("Hari Anak Perempuan", "International Day of the Girl"),
    "10-13": ("Hari Pengurangan Bencana", "Disaster Reduction Day"),
    "10-14": ("Hari Standar Sedunia", "World Standards Day"),
    "10-20": ("Hari Statistik Sedunia", "World Statistics Day"),
    "10-31": ("Hari Kota Sedunia", "World Cities Day"),
    "11-06": ("Hari Anti Perang", "Anti-War Day"),
    "11-19": ("Hari Toilet Sedunia", "World Toilet Day"),
    "11-29": ("Hari Solidaritas Palestina", "Palestine Solidarity Day"),
    "12-20": ("Hari Solidaritas Kemanusiaan", "Human Solidarity Day"),
    # ---- TAMBAHAN BARU: HARI PERINGATAN INTERNASIONAL ----
    "02-21": ("Hari Bahasa Ibu Sedunia", "International Mother Language Day"),
    "04-12": ("Hari Penerbangan Antariksa Manusia", "International Day of Human Space Flight"),
    "06-13": ("Hari Kesadaran Albinisme Sedunia", "International Albinism Awareness Day"),
    "11-17": ("Hari Mahasiswa Internasional", "International Students' Day"),
}

# ---- FUNGSI UTAMA ----
def get_holidays_for_year(year, lang="id"):
    result = {}
    
    # ---- API DINONAKTIFKAN SEMENTARA UNTUK KECEPATAN ----
    # api_result = _fetch_from_apis(year)   # comment
    api_result = None
    if api_result:
        result.update(api_result)
        print(f"[Holidays] ✅ API berhasil untuk {year}: {len(api_result)} hari libur")
    else:
        print(f"[Holidays] ⚠️ API dinonaktifkan, pakai data statis untuk {year}")
    
    # Religi
    religious = RELIGIOUS_HOLIDAYS.get(year, {})
    for mmdd, (name_id, name_en) in religious.items():
        date_str = f"{year}-{mmdd}"
        if date_str not in result:
            result[date_str] = (name_id, name_en)
    
    # Statis nasional
    static_national = STATIC_HOLIDAYS.get("id", {})
    for mmdd, (name_id, name_en) in static_national.items():
        date_str = f"{year}-{mmdd}"
        if date_str not in result:
            result[date_str] = (name_id, name_en)
    
    # Internasional
    for mmdd, (name_id, name_en) in INTERNATIONAL_DAYS.items():
        date_str = f"{year}-{mmdd}"
        if date_str not in result:
            result[date_str] = (f"{name_id} (Internasional)", f"{name_en} (International)")
    
    print(f"[Holidays] Total hari libur/peringatan untuk {year}: {len(result)}")
    return result


def _fetch_from_apis(year):
    # Fungsi ini tidak dipakai karena dinonaktifkan, tapi tetap ada
    return None


def _translate_holiday_name(name_en):
    translations = {
        "New Year's Day": "Tahun Baru Masehi",
        "Independence Day": "Hari Kemerdekaan",
        "Christmas Day": "Hari Natal",
        "Eid al-Fitr": "Idul Fitri",
        "Eid al-Adha": "Idul Adha",
        "Islamic New Year": "Tahun Baru Islam",
        "Prophet Muhammad's Birthday": "Maulid Nabi Muhammad",
        "International Workers' Day": "Hari Buruh Internasional",
        "Good Friday": "Jumat Agung",
        "Ascension Day": "Kenaikan Yesus Kristus",
        "Whit Monday": "Hari Raya Pentakosta",
        "Vesak": "Waisak",
        "Nyepi": "Hari Raya Nyepi",
        "Chinese New Year": "Tahun Baru Imlek",
    }
    for eng, indo in translations.items():
        if eng in name_en:
            return indo
    return name_en


def get_holiday_name(date_str, lang="id"):
    try:
        year = int(date_str[:4])
        holidays = get_holidays_for_year(year, lang)
        if date_str in holidays:
            name_tuple = holidays[date_str]
            if isinstance(name_tuple, tuple):
                return name_tuple[0] if lang == "id" else name_tuple[1]
            else:
                return name_tuple
    except:
        pass
    return ""


def debug_print_holidays(year=None):
    if year is None:
        year = datetime.now().year
    holidays = get_holidays_for_year(year)
    print(f"\n=== HOLIDAYS FOR {year} ===")
    for date_str, names in sorted(holidays.items()):
        if isinstance(names, tuple):
            print(f"{date_str}: {names[0]} / {names[1]}")
        else:
            print(f"{date_str}: {names}")
    print(f"Total: {len(holidays)} days")

if __name__ == "__main__":
    debug_print_holidays(2025)
    debug_print_holidays(2026)
    debug_print_holidays(2027)