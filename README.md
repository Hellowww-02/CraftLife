# ⛏️ CraftLife Desktop

<div align="center">

<img src="assets/banner.png" alt="CraftLife Banner" width="100%">

# CraftLife Desktop

### A Minecraft-inspired RPG Habit Tracker built with **PyQt6**

Turn your real-life habits into an RPG adventure.

Earn **XP**, collect **Gold**, defeat bosses, adopt pets, level up your character, manage your finances, monitor your health, and become the strongest version of yourself.

<br>

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-6.x-41CD52?style=for-the-badge&logo=qt&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blue?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active%20Development-orange?style=for-the-badge)

</div>

---

# 📖 Overview

CraftLife is an **all-in-one desktop productivity application** inspired by RPG games such as **Minecraft** and **Habitica**.

Unlike traditional habit trackers, CraftLife transforms everyday activities into meaningful in-game progression. Completing habits rewards you with **Experience (XP)**, **Gold**, achievements, and character progression, making self-improvement both engaging and rewarding.

Whether you're managing your daily habits, personal finances, health, study schedule, or collaborating with friends in guilds, CraftLife keeps everything in one immersive application.

---

# ✨ Why CraftLife?

Instead of asking:

> "Did you finish your task today?"

CraftLife asks:

> "Did your character become stronger today?"

Every completed habit contributes to your real life **and** your in-game journey.

---

# 🎮 Core Features

## 📝 Productivity

- Habit Tracker
- Daily Tasks
- Quests
- Folder Organization
- Drag & Drop
- Streak System
- XP Rewards
- Gold Rewards
- Daily Progress
- Smart Statistics

---

## ⚔️ RPG System

- Character Level
- Experience (XP)
- Gold Economy
- Inventory
- Shop
- Equipment
- Weapons
- Armor
- Consumables
- Boss Battles
- Guild System
- Friends
- Character Classes
- Achievement System
- Leaderboard

Choose your class:

- ⚔ Warrior
- 🧙 Mage
- 🏹 Archer
- ❤️ Healer
- 🗡 Rogue

---

## 💰 Economy

Manage your personal finances.

- Income
- Expenses
- Debt
- Installments
- Savings
- Investments
- Subscriptions
- Financial Reports
- Charts

---

## ❤️ Health

Track your body and lifestyle.

- Calories
- Protein
- Carbohydrates
- Fat
- Water Intake
- Weight
- Heart Rate
- Mood
- Stress
- Sleep
- Steps
- Sport Activities

Includes **360+ built-in foods** with nutrition data.

---

## 📅 Utilities

- Rich Text Notes
- Calendar
- Holiday Calendar
- Reminders
- Export
- Backup
- Statistics
- Search
- Custom Categories

---

## 🌎 Personalization

- Indonesian Language
- English Language
- Theme Selection
- Avatar
- Bio
- Currency
- Display Name
- Profile Settings

---

# 📊 Feature Overview

| Module | Description |
|---------|-------------|
| Habits | Build positive habits with streaks and rewards |
| Dailies | Repeat daily activities automatically |
| Quests | Long-term goals |
| Sport | Exercise tracking and sport leveling |
| Economy | Complete personal finance management |
| Health | Nutrition, sleep, calories and wellness |
| Shop | Buy equipment and consumables |
| Pets | Adopt pets with passive buffs |
| Guild | Team up and defeat bosses |
| Friends | Friend system and chat |
| Notes | Rich text note editor |
| Calendar | Holiday calendar and custom events |
| Reminders | Desktop reminder system |
| Statistics | Beautiful progress charts |
| Achievements | Unlock rewards |
| Export | CSV, Excel, Word and PDF |

---

# 📸 Screenshots

> Replace these placeholder images with your actual screenshots.

| Dashboard | Habits | Economy |
|------------|---------|----------|
| ![](assets/screenshots/dashboard.png) | ![](assets/screenshots/habits.png) | ![](assets/screenshots/economy.png) |

| Boss Battle | Health | Statistics |
|-------------|---------|------------|
| ![](assets/screenshots/boss.png) | ![](assets/screenshots/health.png) | ![](assets/screenshots/statistics.png) |

---

# 🖥️ System Requirements

| Component | Minimum |
|------------|----------|
| Operating System | Windows 10 / 11 (64-bit) |
| Python | 3.10 or newer |
| RAM | 4 GB |
| Storage | 200 MB |
| Resolution | 1280×720 |

Running from source is also supported on Linux and macOS.

---

# 🚀 Quick Start

## Clone Repository

```bash
git clone https://github.com/Hellowww-02/CraftLife.git

cd CraftLife
```

---

## Create Virtual Environment (Recommended)

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

If you don't have the requirements file yet:

```bash
pip install -r requirements.txt

# Alternatif instalasi manual:
pip install PyQt6 PyQtDarkTheme requests tzlocal mutagen python-dateutil matplotlib openpyxl python-docx reportlab
```

---

## Launch CraftLife

```bash
python MainPyQt6.py
```

The application will automatically create its local database during the first launch.

> **Dependency note:** `mutagen` is required by the Music page for audio metadata and embedded lyrics. `python-dateutil` is used for monthly/yearly subscription date calculation. Both are included in `requirements.txt`.

---

# 📂 Project Structure (Overview)

```text
CraftLife/
│
├── MainPyQt6.py
├── database.py
├── translations.py
├── food_data.py
├── holidays.py
│
├── modules/
├── ui/
├── icons/
├── assets/
├── backups/
│
├── README.md
├── LICENSE
├── requirements.txt
└── .gitignore
```

---

# 🖥️ Complete Usage Guide

CraftLife is divided into several modules. Each module focuses on a different aspect of your real-life progression while contributing to your RPG character.

---

# 🔐 Authentication

## Register

Create a new account by providing:

- Username
- Password
- Security Question
- Character Class

Choose one of five starter classes:

- ⚔ Warrior
- 🧙 Mage
- 🏹 Archer
- ❤️ Healer
- 🗡 Rogue

---

## Login

Simply enter your username and password.

Optional features:

- Remember Me
- Auto Login
- Backup Codes
- Password Recovery

---

# 🏠 Dashboard

The dashboard is your adventure hub.

It displays:

- 🎖 Player Level
- ⭐ XP
- ❤️ HP
- 🔵 MP
- 💰 Gold
- 📅 Current Date
- 🕒 Digital Clock
- 📊 Daily Progress

You can quickly navigate to every module using the left sidebar.

---

# 📝 Habits

The Habit module helps build long-term positive habits.

Features:

- Create unlimited habits
- Custom icons
- Difficulty levels
- Custom folders
- XP rewards
- Gold rewards
- Streak tracking
- Drag & Drop
- Search
- Filtering

Completing a habit grants rewards based on its difficulty.

---

# 📆 Dailies

Dailies are recurring tasks that reset every day.

Examples:

- Drink Water
- Read Books
- Pray
- Exercise
- Meditation

Failing to complete a daily may reduce your streak.

Special consumables such as **Ice Blocks** can protect your streak.

---

# 🎯 Quests

Quests represent long-term objectives.

Examples:

- Read 10 Books
- Lose 5 kg
- Save $1000
- Complete Programming Course

Rewards are significantly larger than Habits.

---

# 🏃 Sport Tracker

Record all physical activities.

Supported information:

- Activity Type
- Duration
- Intensity
- Calories Burned
- Notes

Gain Sport Points to increase your Sport Level.

---

# ❤️ Health Tracker

Monitor your health every day.

Supported logs:

- Calories
- Protein
- Carbohydrates
- Fat
- Water Intake
- Weight
- Heart Rate
- Mood
- Stress
- Sleep
- Steps

CraftLife includes a built-in database containing **360+ foods** with nutritional values.

Charts automatically visualize your weekly progress.

---

# 💰 Economy Tracker

Manage every aspect of your personal finance.

Features include:

## Income

Track salary, allowance, gifts, freelance income and more.

---

## Expenses

Categorize spending such as:

- Food
- Transportation
- Shopping
- Entertainment
- Bills

---

## Debt

Manage debts using installment tracking.

Receive reminders before due dates.

---

## Savings

Create multiple savings goals.

Examples:

- Laptop
- Vacation
- Emergency Fund

---

## Investments

Track:

- Stocks
- Cryptocurrency
- Mutual Funds
- Gold
- Other Investments

---

## Subscriptions

Monitor recurring subscriptions such as:

- Spotify
- Netflix
- ChatGPT
- Cloud Storage

Automatic reminders prevent missed payments.

---

# 🛒 Shop

Spend your Gold on useful items.

Categories include:

- Weapons
- Armor
- Consumables
- Potions
- Legendary Items
- Decorations

Items provide various gameplay bonuses.

---

# 🐾 Pets

Collect companions that help your journey.

Features:

- 20+ Pets
- Passive Buffs
- Upgrade System
- Equip / Unequip

Higher player levels unlock additional pet slots.

---

# ⚔️ Guild System

Create or join guilds with friends.

Guild features:

- Guild Chat
- Guild Members
- Shared Progress
- Boss Battles
- Leaderboards

Guilds encourage teamwork and accountability.

---

# 👹 Boss Battles

One of CraftLife's signature features.

Guild members work together to defeat powerful bosses.

Each player can perform:

- ⚔ Light Attack
- 💥 Heavy Attack
- 🛡 Block
- ✨ Ultimate Skill

Rewards include:

- XP
- Gold
- Rare Items
- Achievements

Boss battles are limited each day to maintain balance.

---

# 👥 Friends

Connect with other CraftLife players.

Features:

- Friend Requests
- Friend List
- Online Status
- Real-time Chat
- Shared Statistics

---

# 📝 Notes

A fully featured note-taking system.

Supports:

- Rich Text
- Folder Structure
- Subfolders
- Search
- Formatting
- Lists

Useful for school, work, or personal planning.

---

# 🔔 Reminders

Never miss important tasks.

Features:

- Desktop Notifications
- Sound Alerts
- Custom Reminder Time
- Repeat Schedule
- Custom Audio

---

# 📅 Calendar

View an annual calendar containing:

- National Holidays
- International Holidays
- Personal Events
- Daily Notes

---

# 📊 Statistics

Analyze your progress with detailed charts.

Includes statistics for:

- XP
- Gold
- Habits
- Health
- Economy
- Sports
- Achievements

Charts update automatically.

---

# 🏆 Achievements

Unlock achievements by completing milestones.

Examples:

- First Habit
- 100-Day Streak
- Rich Adventurer
- Guild Master
- Health Champion

Achievements reward XP and Gold.

---

# 👤 Profile

Customize your character.

Editable fields:

- Display Name
- Avatar
- Emoji
- Biography
- Class
- Theme
- Language

---

# ⚙️ Settings

Configure the application.

Options include:

- Language
- Theme
- Currency
- Password
- Backup
- Notifications
- Security
- Database

---

# 🗄️ Database

CraftLife stores all user data locally using SQLite.

Default location:

### Windows

```
%APPDATA%/CraftLife/
```

### Linux

```
~/.local/share/CraftLife/
```

### macOS

```
~/Library/Application Support/CraftLife/
```

Database features:

- SQLite
- WAL Mode
- Auto Checkpoint
- High Performance
- Crash Recovery

---

# 💾 Backup

CraftLife automatically protects your data.

Features:

- Automatic Backup
- Manual Backup
- Restore Backup
- Crash Recovery

Older backups can be automatically removed to save storage.

---

# 📤 Export

Export your data into multiple formats.

Supported formats:

- CSV
- Excel (.xlsx)
- Word (.docx)
- PDF

Exports include statistics, economy, health, habits and more.

---

# 🌍 Multi-language

Supported languages:

| Language | Code |
|-----------|------|
| Indonesian | id |
| English | en |

Language switching is instant and does not require restarting the application.

---

# 🎨 Themes

Choose your favorite Minecraft-inspired theme.

| Theme | Primary Color |
|---------|---------------|
| 🌿 Overworld | Green |
| 🔥 Nether | Red |
| 🌌 The End | Purple |
| 🌊 Ocean | Blue |
| 🏛 Ancient City | Dark Teal |

Themes affect the entire user interface.

---

# 🔒 Security

CraftLife prioritizes user privacy.

Features include:

- Local Database
- Password Protection
- Security Questions
- Backup Codes
- Session Management

No personal data is shared without your permission.

---

# 🤝 Contributing

Thank you for considering contributing to CraftLife!

Whether you are fixing bugs, improving documentation, designing UI, or implementing new features, every contribution is appreciated.

---

## How to Contribute

### 1. Fork the repository

Click the **Fork** button on GitHub.

---

### 2. Clone your fork

```bash
git clone https://github.com/Hellowww-02/CraftLife.git

cd CraftLife
```

---

### 3. Create a new branch

```bash
git checkout -b feature/amazing-feature
```

---

### 4. Make your changes

Please follow the project coding standards.

---

### 5. Commit your changes

```bash
git commit -m "Add amazing feature"
```

---

### 6. Push

```bash
git push origin feature/amazing-feature
```

---

### 7. Open a Pull Request

Describe:

- What you changed
- Why you changed it
- Screenshots (if applicable)

---

# 📐 Coding Standards

Please follow these guidelines.

## Python

- Follow **PEP 8**
- Use meaningful variable names
- Avoid duplicated code
- Write reusable functions
- Keep functions small

---

## Documentation

Every public function should include a docstring.

Example:

```python
def calculate_xp(level: int) -> int:
    """
    Calculate XP required for the next level.

    Parameters
    ----------
    level : int

    Returns
    -------
    int
    """
```

---

## UI

Please maintain CraftLife's visual style.

- Minecraft-inspired
- Dark Mode friendly
- Consistent spacing
- Rounded corners
- Pixel-friendly icons

---

# 📂 Branch Naming

Examples:

```
feature/guild-chat

feature/cloud-sync

bugfix/login

refactor/database

docs/readme

ui/settings-page
```

---

# 🐛 Reporting Bugs

Please include:

- Operating System
- Python Version
- CraftLife Version
- Error Message
- Steps to Reproduce
- Screenshot

---

# 💡 Feature Requests

Suggestions are always welcome.

Examples:

- New RPG mechanics
- More pets
- Better economy system
- Cloud synchronization
- Mobile version

---

# ❓ Frequently Asked Questions

## Does CraftLife require internet?

No.

CraftLife works completely offline.

Internet is only used for optional features such as:

- Time synchronization
- Future cloud features

---

## Is my data stored online?

No.

Everything is stored locally using SQLite.

---

## Can I backup my data?

Yes.

Automatic backups are supported.

Manual backups are available in:

Settings → Backup

---

## Can I transfer my data?

Yes.

Simply copy your database or export your data.

---

## Is Linux supported?

Yes.

Run the project directly from source.

---

## Is macOS supported?

Yes.

Source code is supported.

Native testing is still ongoing.

---

# 🐞 Troubleshooting

## ModuleNotFoundError

Install dependencies.

```bash
pip install -r requirements.txt
```

---

## Database Locked

Close any other application using the database.

Restart CraftLife.

---

## Icons Missing

Ensure the **icons/** directory exists.

---

## Export Failed

Install

- openpyxl
- python-docx
- reportlab

---

## Build Failed

Update PyInstaller.

```bash
pip install -U pyinstaller
```

---

## Session Not Saved

Check write permission for:

Windows

```
%APPDATA%/CraftLife
```

Linux

```
~/.local/share/CraftLife
```

---

## Application Crash

Please attach:

- Error.txt
- crash.log
- Screenshot

when creating a GitHub Issue.

---

# 🛣 Roadmap

## Version 1.x

- [x] Habit Tracker
- [x] Daily Tasks
- [x] Quest System
- [x] Health Tracker
- [x] Economy Tracker
- [x] Notes
- [x] Calendar
- [x] Reminder
- [x] Statistics
- [x] Export
- [x] Backup

---

## Version 2.x

- [ ] Cloud Sync
- [ ] Google Login
- [ ] Discord Login
- [ ] Online Friends
- [ ] Trading System
- [ ] Marketplace
- [ ] Guild Ranking
- [ ] Seasonal Events

---

## Version 3.x

- [ ] Android Version
- [ ] iOS Version
- [ ] Steam Release
- [ ] Multiplayer Guild Dungeon
- [ ] AI Habit Coach
- [ ] Achievement Sharing

---

# 🏗 Project Status

Current Status

> 🚧 Active Development

CraftLife is continuously improving.

New features and optimizations are added regularly.

---

# 📈 Future Goals

Our long-term vision includes:

- Cross-platform desktop support
- Mobile companion application
- Cloud synchronization
- Multiplayer RPG
- Community plugins
- AI-powered productivity assistant

---

# 📄 License

This project is licensed under the **MIT License**.

See the **LICENSE** file for complete information.

---

# 🙏 Acknowledgements

Special thanks to these amazing projects:

- Python
- PyQt6
- SQLite
- ReportLab
- OpenPyXL
- python-docx
- Matplotlib
- Requests
- tzlocal

Inspirations:

- Minecraft
- Habitica
- Notion
- Obsidian

---

# 👨‍💻 Developer

**CraftLife Team**

Built with ❤️ using Python and PyQt6.

---

# 🌟 Support the Project

If you enjoy CraftLife, please consider supporting the project.

⭐ Star this repository

🐛 Report bugs

💡 Suggest new features

🤝 Contribute code

Every contribution helps CraftLife become even better.

---

# 📬 Contact

GitHub Issues

Use GitHub Issues for:

- Bug reports
- Feature requests
- Questions
- Discussions

---

<div align="center">

# ⛏️ CraftLife Desktop

### Build Better Habits.
### Become Stronger Every Day.

⭐ Thank you for visiting this repository!

Made with ❤️ by the CraftLife Team.

</div>
