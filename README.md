````markdown
# ⛏️ CraftLife Desktop

> **A Minecraft-inspired RPG Habit Tracker built with PyQt6**

CraftLife is an all-in-one productivity desktop application that combines **habit tracking**, **personal finance**, **health monitoring**, and **RPG mechanics** into a single experience.

Instead of simply checking off tasks, users earn **XP**, **Gold**, level up their character, collect pets, fight bosses, manage guilds, and build better habits while having fun.

---

## 📸 Preview

![CraftLife Banner](https://via.placeholder.com/1200x350/2d2d2d/6db33f?text=CraftLife+Desktop)

---

# ✨ Features

## 📝 Productivity

- Habit Tracker
- Daily Tasks
- Quests
- Folder Organization
- Drag & Drop
- Streak System
- XP & Gold Rewards

---

## 🏃 Health

- Food Tracker
- Water Intake
- Weight Log
- Sleep Tracker
- Mood Tracking
- Heart Rate
- Step Counter
- Calories
- Nutrition Database (360+ foods)

---

## 💰 Economy

- Income
- Expense
- Debt Management
- Installments
- Savings
- Investments
- Subscription Tracking
- Financial Statistics

---

## ⚔️ RPG

- Character Level
- XP System
- Gold
- Pets
- Equipment
- Shop
- Guild
- Boss Battles
- Character Classes

Choose between:

- ⚔ Warrior
- 🧙 Mage
- 🏹 Archer
- ❤️ Healer
- 🗡 Rogue

---

## 👥 Social

- Friend Requests
- Real-time Chat
- Guild System
- Leaderboards

---

## 📅 Utilities

- Rich Text Notes
- Calendar
- Holiday Calendar
- Reminders
- Statistics
- Achievement System
- Data Export

---

## 🌍 Customization

- Indonesian & English
- Multiple Themes
- Currency Selection
- Avatar Customization
- Profile Settings

---

# 📋 Feature Overview

| Module | Description |
|---------|-------------|
| Habits | Build better habits with streaks and rewards |
| Dailies | Daily recurring tasks |
| Quests | Long-term missions |
| Sport Tracker | Exercise logging and sport level |
| Economy | Complete financial management |
| Health | Calories, nutrition, sleep, water and more |
| Pets | Unlock pets with passive buffs |
| Shop | Buy equipment and consumables |
| Guild | Create guilds and defeat bosses |
| Friends | Add friends and chat |
| Notes | Rich text note system |
| Calendar | Holiday calendar with custom notes |
| Reminders | Notification & sound reminders |
| Stats | Detailed statistics |
| Achievements | Unlock rewards |
| Export | CSV, Excel, Word and PDF |

---

# 📋 System Requirements

| Component | Minimum |
|------------|----------|
| OS | Windows 10/11 (64-bit) |
| Python | 3.10+ |
| RAM | 4 GB |
| Storage | 200 MB |
| Resolution | 1280×720 |

Linux and macOS are supported when running from source.

---

# 🚀 Installation

## Clone Repository

```bash
git clone https://github.com/username/craftlife-desktop.git
cd craftlife-desktop
```

---

## (Optional) Create Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

If `requirements.txt` is unavailable:

```bash
pip install PyQt6 requests tzlocal openpyxl matplotlib python-docx reportlab
```

---

## Run

```bash
python MainPyQt6.py
```

The database will automatically be created at:

### Windows

```
%APPDATA%\CraftLife\
```

### Linux/macOS

```
~/.local/share/CraftLife/
```

---

# 🛠 Building Executable (.exe)

Install PyInstaller

```bash
pip install pyinstaller
```

Build:

```bash
pyinstaller --onefile --windowed ^
--add-data "database.py;." ^
--add-data "food_data.py;." ^
--add-data "holidays.py;." ^
--add-data "translations.py;." ^
--add-data "icons;icons" ^
--icon "icons/craftlife.ico" ^
MainPyQt6.py
```

Output:

```
dist/MainPyQt6.exe
```

---

# 📁 Project Structure

```
CraftLife/
│
├── MainPyQt6.py
├── database.py
├── food_data.py
├── holidays.py
├── translations.py
├── requirements.txt
├── LICENSE
├── README.md
│
├── icons/
│
├── modules/
│
├── assets/
│
└── backups/
```

---

## 🚫 Do NOT Upload

```
craftlife.db

session.json

Error.txt

crash.log

__pycache__/

build/

dist/

*.spec
```

---

# 🖥 Quick Guide

## Login

- Register
- Login
- Remember Me

---

## Dashboard

Displays

- Level
- XP
- HP
- MP
- Gold
- Clock

---

## Habits

- Add Habit
- Complete Habit
- Earn XP
- Earn Gold
- Build Streak

---

## Sport

Track

- Activity
- Duration
- Calories
- Sport Level

---

## Economy

Manage

- Income
- Expenses
- Debt
- Savings
- Investments

---

## Health

Track

- Calories
- Protein
- Carbs
- Fat
- Water
- Sleep
- Weight
- Mood

---

## Guild

- Create Guild
- Join Guild
- Fight Bosses
- Daily Boss Limit

---

## Pets

- Adopt Pets
- Equip Pets
- Passive Buffs

---

## Notes

- Rich Text
- Search
- Folder
- Reminder

---

## Calendar

- Holidays
- Notes
- Year View

---

## Statistics

- Progress
- Charts
- Exports

---

# 🗄 Database

Location:

Windows

```
%APPDATA%\CraftLife\
```

Linux

```
~/.local/share/CraftLife/
```

Features:

- SQLite
- WAL Mode
- Auto Checkpoint
- Auto Backup
- Manual Backup

---

# 🌍 Languages

| Language | Code |
|------------|------|
| Indonesian | id |
| English | en |

Language changes apply instantly.

---

# 🎨 Themes

| Theme | Color |
|---------|-----------|
| 🌿 Overworld | Green |
| 🔥 Nether | Red |
| 🌌 The End | Purple |
| 🌊 Ocean | Blue |
| 🏚 Ancient City | Dark Green |

---

# 📸 Screenshots

Replace these with your own screenshots.

| Dashboard | Boss Battle | Economy |
|------------|------------|------------|
| Screenshot | Screenshot | Screenshot |

---

# 🤝 Contributing

Contributions are always welcome.

1. Fork Repository

2. Create Branch

```bash
git checkout -b new-feature
```

3. Commit

```bash
git commit -m "Add new feature"
```

4. Push

```bash
git push origin new-feature
```

5. Open Pull Request

---

# 🐛 Troubleshooting

| Problem | Solution |
|------------|------------|
| ModuleNotFoundError | Install requirements |
| Database Locked | Close other instances |
| Missing Icon | Check icons folder |
| Export Failed | Install export libraries |
| Session Missing | Check AppData permissions |

---

# 📄 License

Distributed under the MIT License.

See **LICENSE** for more information.

---

# 🙏 Credits

Built with

- Python
- PyQt6
- SQLite
- Requests
- tzlocal
- Matplotlib
- OpenPyXL
- python-docx
- ReportLab

Inspired by

- Habitica
- Minecraft

---

# 📧 Support

Developer

**CraftLife Team**

Issues

Open a GitHub Issue.

Feature requests are always welcome.

---

# 🗺 Roadmap

- ✅ Desktop Version
- 🔄 Better Inventory
- 🔄 Friend Trading
- 🔄 Mini Games
- 🔄 Cloud Sync
- 🔄 Mobile Version
- 🔄 Steam Release
- 🔄 Linux Improvements
- 🔄 macOS Support
- 🔄 Plugin System

---

# ⭐ Support the Project

If you enjoy CraftLife, consider giving the repository a **⭐ Star**.

It helps more people discover the project and motivates future development.

Happy adventuring!

⛏️ **CraftLife Desktop**
````
