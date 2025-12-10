# GamesManagerV2 🎮

> **⚠️ IMPORTANT NOTICE / LEGAL DISCLAIMER**
> 
> This program was created **solely for educational, learning, and practice purposes**. 
> I, the developer, have **no affiliation** with any platforms, services, or games that this program might access or interact with.
> 
> **Use of this software is entirely at your own risk.** 
> The developer assumes **no liability** for any damages, legal violations, account bans, data loss, or other consequences resulting from the use of this program. This is a proof-of-concept project designed to demonstrate programming capabilities in automation, UI design, and network handling. I do not endorse or encourage software piracy.

---

## 📖 About The Project

**GamesManagerV2** is a comprehensive Python-based desktop application developed as a sophisticated learning project. The primary goal was to challenge myself in various aspects of software engineering, moving beyond simple scripts to a complex, multi-threaded GUI application.

This project serves as a practical exploration into:
*   **Advanced Python Programming**: Utilizing complex data structures and object-oriented design.
*   **GUI Development**: Building a modern, responsive, and dark-themed user interface using **PyQt5**.
*   **Web Scraping & Automation**: implementing robust scrapers using **Selenium** and **Undetected Chromedriver** to navigate complex web security (like Cloudflare).
*   **Network Engineering**: creating a custom download manager capable of handling multi-part downloads, resuming, and bandwidth management.
*   **File System Management**: Automated handling of archives (RAR extraction), file organization, and configuration parsing (`.ini` manipulation).

## ✨ Key Features

### 📚 Interactive Library
*   **Visual Collection**: Displays your game collection with high-quality cover art.
*   **Detailed View**: Shows comprehensive game info including version, playtime tracking, and categories.
*   **Media Gallery**: Automatically fetches and displays screenshots for each game to provide a rich visual experience.
*   **Playtime Tracker**: Monitors how long you've played each title.

### 🔍 Integrated Search & Scraper
*   **Universal Scraper**: A custom-built scraping engine that navigates protection layers to find content.
*   **Live Search**: Search for titles directly within the application.
*   **One-Click Add**: Easily add found games to your library or download queue.

### ⬇️ Advanced Download Manager
*   **Multi-Source Support**: Architected to handle various file hosting providers (e.g., Gofile, 1Fichier, Buzzheavier).
*   **Resumable Downloads**: Capable of pausing and resuming downloads without data loss.
*   **Multi-Threading**: Uses threading to download files in parallel parts for maximum speed.
*   **Auto-Extraction**: Automatically extracts downloaded archives (RAR/ZIP) and organizes them into the game directory.

### ⚙️ Automation & Configuration
*   **Config Auto-Patcher**: Automatically updates game configuration files (`.ini`, `.txt`) with your preferred username and language settings.
*   **Cache Management**: Smart caching of images to speed up loading, with tools to clean up unused assets.
*   **Self-Updating**: Includes logic for checking and managing application updates.

## 🛠️ Technical Stack

This project leverages a powerful stack of Python libraries:

*   **GUI**: `PyQt5` (Qt for Python)
*   **Web Automation**: `selenium`, `undetected-chromedriver`
*   **Parsing**: `BeautifulSoup4`, `lxml`
*   **Networking**: `requests`
*   **System**: `psutil`, `pywin32`
*   **Archives**: `rarfile` (requires WinRAR/UnRAR)

## 🚀 Getting Started

### Prerequisites
*   Python 3.8+
*   Google Chrome (for the scraper)
*   WinRAR (for extraction features)

### Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/yourusername/GamesManagerV2.git
    cd GamesManagerV2
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Application**
    ```bash
    python main.py
    ```

## 🖥️ Usage Guide

1.  **Search Tab**: Enter the name of a game you want to research. The scraper will fetch results. Select a game to see details.
2.  **Library Tab**: View games you have "installed" or added to your collection. Click on a game to view screenshots, launch it, or manage its files.
3.  **Downloads Tab**: Monitor active downloads. You can pause, resume, or stop downloads here.
4.  **Settings Tab**:
    *   Set your **Default Username** and **Language**.
    *   Click **"Apply to All Games"** to auto-edit the `.ini` files of your installed games to match these settings.
    *   Use **"Clean Cache"** to free up space by removing images for games you no longer have.

---

*This project is archived and maintained for portfolio purposes only.*
