# the________says
a cute little project that lets you dump your favorite artsy band's lyrics into plaintext so you can make neat art with them

for the hardware components to this project, see `HARDWARE.md` in `/docs`.

# Setup

## macOS

Install [Homebrew](https://brew.sh) if you don't have it — it's the standard package manager for macOS.
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Install Python 3.
```bash
brew install python
```

Clone the repo and run setup. This creates a virtual environment, installs dependencies, and scaffolds your `.env`.
```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo
chmod +x setup.sh && ./setup.sh
```

---

## Windows

Install [Scoop](https://scoop.sh) — a command-line package manager that doesn't require admin rights.
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
irm get.scoop.sh | iex
```

Install Python 3 and Git.
```powershell
scoop install python git
```

Clone the repo. Then run setup from Git Bash (not PowerShell — the script requires bash).
```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo
chmod +x setup.sh && ./setup.sh
```

---

## Debian / Ubuntu

Update your package index, then install Python 3, pip, and Git.
```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git
```

Clone the repo and run setup.
```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo
chmod +x setup.sh && ./setup.sh
```

---

## After setup

`setup.sh` will create a `.env` file from `.env.example`. Open it and add your Genius API token — get one free at [genius.com/api-clients](https://genius.com/api-clients).

```
GENIUS_TOKEN=your_token_here
```

Then run the script:
```bash
source .venv/bin/activate
python3 fetch_lyrics.py
```

Lyrics are saved to `lyrics/` as individual `.txt` files. That folder is gitignored — its contents will never be committed.

To reset the virtual environment and start fresh:
```bash
rm -rf .venv && ./setup.sh
```

---

## Todo

- **Dynamic CSS selector detection** — Genius has already broken `lyricsgenius`'s scraper once by quietly changing their page markup. A more resilient approach would be to fetch a known lyrics page on startup, inspect the DOM for likely lyrics containers (large text blocks with line-break structure, low link density), and infer the correct selector automatically rather than hardcoding `div[data-lyrics-container="true"]`.

- **Shell agnosticism** — `setup.sh` currently targets bash and zsh on macOS/Linux and Git Bash on Windows. Proper POSIX `sh` compatibility would broaden support without much effort.

- **Artist as a CLI argument** — `ARTIST` is currently hardcoded in `fetch_lyrics.py`. Exposing it as a flag (`--artist "Bon Iver"`) would make the script reusable without editing the source.

- **hardware outputs** — buil the scripts that will run on the pi zero, bluetooth to p-otouch label makers, and use local llms to group lyrics for fun mix and matches

- **game** — script that will generate apples-to-apples type games based on your fav artists's lyrics so your friends can have artsy fun game nights 