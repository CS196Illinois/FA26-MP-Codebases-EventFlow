# EventFlow

**CS 124H · Fall 2026 · MP Codebase**

A campus events website. It collects UIUC events in one place, uses AI to pull events out of pasted text or emails, and adds them to a shared Google Calendar.

Built by a CS 124H team in Fall 2025 with Python Flask website, Firebase database, Google Calendar, and an AI model via OpenRouter.

> **Your job in this MP:** you're joining a project someone else wrote, just like starting a
> new job. Read the code, get it running, then **fix, improve, or change something** and
> submit it as a **pull request**. Bugs and rough edges are expected. Finding them is part
> of the work. [`Docs/RUN.md`](Docs/RUN.md) has deeper technical notes and known issues.

---

## Contents

1. [One-time setup](#1-one-time-setup)
2. [Get your own copy of the code](#2-get-your-own-copy-of-the-code)
3. [Add the config files](#3-add-the-config-files)
4. [Run the project](#4-run-the-project)
5. [Make your changes](#5-make-your-changes)
6. [Submit a pull request](#6-submit-a-pull-request)
7. [Update your pull request](#7-update-your-pull-request)
8. [Troubleshooting](#8-troubleshooting)
9. [Words you'll see](#9-words-youll-see)

**How to read the commands:** text in grey boxes like `git status` is something you type
into a **terminal** (macOS: the *Terminal* app; Windows: *PowerShell*; Linux: your terminal),
then press **Enter**. Anything after a `#` is a note for you, not part of the command.
Replace words in CAPITALS, like `YOUR-USERNAME`, with your own value.

---

## 1. One-time setup

Do this once per computer.

**a. Make a GitHub account** at <https://github.com/signup> if you don't have one.

**b. Install Git:** <https://git-scm.com/downloads>. Check it worked: `git --version`.

**c. Install the GitHub CLI**, a tool that handles logging in to GitHub for you:
<https://cli.github.com>. Check it worked: `gh --version`.

**d. Log in to GitHub from the terminal:**
```bash
gh auth login
```
Answer the questions: **GitHub.com** → **HTTPS** → **Yes** (authenticate Git) →
**Login with a web browser**. Copy the one-time code it shows, press Enter, paste the code in
the browser and approve.

**e. Tell Git who you are** (this name and email are attached to your commits):
```bash
git config --global user.name "Your Name"
git config --global user.email "you@illinois.edu"
```

**f. Install what this project needs:**

- **Python 3.12**: <https://www.python.org/downloads/> (pick a 3.12.x release)
  Check it worked: `python3.12 --version` (Windows: `py -3.12 --version`).

**g. A code editor.** We recommend **VS Code**: <https://code.visualstudio.com>.

---

## 2. Get your own copy of the code

You can't change the course's copy directly, so you make your own copy called a **fork**,
then download it to your computer (**clone**).

**a. Fork:** at the top right of this page, click **Fork** → keep **Owner** as your
username → click **Create fork**. You now have
`github.com/YOUR-USERNAME/FA26-MP-Codebases-EventFlow`.

**b. Clone your fork** into a folder on your computer:
```bash
cd ~/Documents          # or wherever you keep your projects
gh repo clone YOUR-USERNAME/FA26-MP-Codebases-EventFlow
cd FA26-MP-Codebases-EventFlow
```
Every command from here on is run **inside this `FA26-MP-Codebases-EventFlow` folder**.
To open it in VS Code: `code .`

---

## 3. Add the config files

EventFlow needs two files from Canvas plus one key you make yourself.

1. Download **`eventflow.env`** and **`service-account.json`** from Canvas into your
   **Downloads** folder.
2. Copy them into the project folder:

   **macOS / Linux**
   ```bash
   cp ~/Downloads/eventflow.env .env
   cp ~/Downloads/service-account.json service-account.json
   ```
   **Windows (PowerShell)**
   ```powershell
   Copy-Item $HOME\Downloads\eventflow.env .env
   Copy-Item $HOME\Downloads\service-account.json service-account.json
   ```
3. Make your own free AI key (everyone needs their own):
   1. Go to <https://openrouter.ai> and sign in (Google or GitHub is fine).
   2. Go to <https://openrouter.ai/settings/keys> and click **Create API Key**.
      Leave "Credit limit" empty. You never need to add money.
   3. Copy the key. It is only shown once.
   4. Open `.env` in your editor and paste it after `OPENAI_KEY=`, so the line looks like
      `OPENAI_KEY=sk-or-v1-...`. Save the file.

**Never share or commit these files.** `.env` and `service-account.json` are secret.
Git is already set to ignore them.

---

## 4. Run the project

Make sure it works **before** you change anything, so you know any later problem came
from your change.

macOS / Linux:
```bash
python3.12 -m venv .venv                   # first time only
source .venv/bin/activate
pip install -r Project/requirements.txt    # first time only
cd Project
python app.py
```
Windows (PowerShell):
```powershell
py -3.12 -m venv .venv                     # first time only
.venv\Scripts\Activate.ps1
pip install -r Project/requirements.txt    # first time only
cd Project
python app.py
```

Open <http://127.0.0.1:5000>. You should see a list of events. Click **+ Add** on one, and it
appears on the shared calendar at the top of the page.

To stop the website, press **Ctrl + C** in the terminal.

---

## 5. Make your changes

**a. Make a branch.** A branch is a separate line of work, so your changes stay apart
from the original code. Name it after what you're doing:
```bash
git switch -c fix-profile-crash      # use your own short name, no spaces
```

**b. Edit the code** in your editor. Save often, and re-run the project to check your work.

**c. See what you changed:**
```bash
git status        # lists changed files
git diff          # shows the exact lines you changed
```

Running EventFlow can change the committed `__pycache__` files. Unless you changed them on
purpose, undo that before you commit:
```bash
git restore Project/__pycache__ Project/email_parser/__pycache__ Project/web_scraper/__pycache__
```

**d. Save a snapshot (commit).** Add the files you changed, then commit with a short
message that says what you did:
```bash
git add PATH/TO/FILE1 PATH/TO/FILE2     # or: git add .   (adds everything listed by git status)
git commit -m "Fix crash on profile page when not logged in"
```
Commit as often as you like. Small commits with clear messages are better than one huge one.

**e. Upload your branch to your fork (push):**
```bash
git push -u origin fix-profile-crash   # first push of a new branch
git push                               # every push after that
```

---

## 6. Submit a pull request

A **pull request (PR)** asks the course repo to look at your changes. It's how you submit.

1. Open your fork on GitHub: `github.com/YOUR-USERNAME/FA26-MP-Codebases-EventFlow`.
2. Click the yellow **Compare & pull request** button. If you don't see it, click
   **Contribute** → **Open pull request**.
3. Check the top bar reads:
   **base repository: `CS196Illinois/FA26-MP-Codebases-EventFlow`** · **base: `main`** ←
   **head repository: `YOUR-USERNAME/FA26-MP-Codebases-EventFlow`** · **compare: `your-branch`**
4. Give it a clear **title**, e.g. *"Fix crash on profile page when not logged in"*.
5. **Fill in every section of the description.** A template appears automatically. Write your
   answers outside the `<!-- -->` comments, and tick the checklist boxes.
6. Click **Create pull request**.

**An automatic check then runs.** Scroll down after a few seconds:
- ✅ **"PR checklist complete"**: you're done. Your PR is submitted.
- ❌ **a comment listing problems**: fix each one. To edit the description, click **···** at
  the top right of your first comment, then **Edit**. The check re-runs when you save.

Staff grade PRs with a passing check. Your PR **won't be merged** into the course repo.
That's expected, because everyone starts from the same original code.

---

## 7. Update your pull request

Want to change something after submitting? Just commit and push to the **same branch**.
The PR updates automatically:
```bash
git add .
git commit -m "Handle the empty-list case too"
git push
```
Don't open a second PR for the same work.

---

## 8. Troubleshooting

**`git push` says "Permission denied" or "403".**
You cloned the course repo instead of your fork. Fix it without losing your work:
```bash
gh repo fork --remote        # makes (or finds) your fork and points "origin" at it
git push -u origin HEAD
```

**"command not found" (`git`, `gh`, `node`, `python3.12`, `flutter`…).**
The tool isn't installed, or the terminal was open before you installed it. Close the
terminal, open a new one, and try again. If it still fails, reinstall from section 1.

**The check says my PR includes a secret file.**
```bash
git rm --cached .env          # use the file name from the bot's comment
git commit -m "Remove secret file"
git push
```
`--cached` removes it from Git but keeps it on your computer.

**I'm on the wrong branch / lost track of where I am.**
`git status` shows your current branch. `git branch` lists all branches.
`git switch BRANCH-NAME` moves to another one.

**I want to throw away my changes to one file.**
`git restore PATH/TO/FILE` puts it back to your last commit. This can't be undone.

**The course repo got updated and I want those changes.**
```bash
git pull upstream main
```

**Something else?** Copy the full error message and ask on the course forum or in office
hours. Error messages are the most useful clue.

---

## 9. Words you'll see

| Word | Meaning |
|---|---|
| **Repository (repo)** | A project folder whose full history Git tracks. |
| **Fork** | Your own copy of someone else's repo on GitHub. |
| **Clone** | Downloading a repo from GitHub to your computer. |
| **Branch** | A separate line of work inside a repo. `main` is the original. |
| **Commit** | A saved snapshot of your changes, with a message. |
| **Push** | Uploading your commits from your computer to GitHub. |
| **Pull request (PR)** | A request asking a repo's owners to review your changes. |
| **`origin`** | Git's nickname for your fork. |
| **`upstream`** | Git's nickname for the course repo you forked from. |
| **`.env` file** | A file of settings and secret keys. It's never committed. |

---

## Original team (Fall 2025)

### Group 7
Group Name: EventFlow

[MVP Link](https://docs.google.com/document/d/1WsX-KeNL8hnaEEFZJ60RM2zYCNZ7Pj1u/edit?usp=sharing)

Team Members: rayluo2, nikhill2, ayaanc2, jrptak2, shubhj3, dawidw2

Project Manager: advaity2
