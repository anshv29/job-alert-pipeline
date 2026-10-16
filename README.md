# Job Alert Pipeline

Get an email when a new internship or co-op is posted at the companies you care about.

It checks company career sites for you, every few hours, and emails you only the new jobs that match. It runs for free on GitHub, so it keeps working while your laptop is closed. You do not need to know how to code.

There are two ready-made versions, picked with one line:

* **finance**: investment banking, sales and trading, equity research, asset management, risk, corporate finance, capital markets, wealth management, accounting, and finance or business analyst internships and co-ops.
* **tech**: software, data, machine learning, and quant internships.

Setup takes about 20 minutes. Nothing in this guide costs money except the optional AI filter in step 4, which is a few cents a day.

---

## What you need

* A Gmail account to send the alerts from. A second, new Gmail just for this is a good idea, because you will create a special password for it.
* The email address where you want to receive the alerts (it can be the same account).
* A GitHub account (free). Step 1 covers this.

---

## Step by step setup

### Step 1. Make a GitHub account

1. Go to https://github.com and click **Sign up**.
2. Follow the steps. Use any email. Pick a username.
3. Check your inbox for the code GitHub sends and enter it.

### Step 2. Make your own private copy

1. Open the page for this project on GitHub (the page you are reading this on).
2. Click the green **Use this template** button near the top right, then **Create a new repository**.
3. Give it a name, for example `my-job-alerts`.
4. Under visibility, choose **Private**. This matters. Your copy will hold your settings and a list of jobs it has seen, and a private copy keeps that to yourself.
5. Click **Create repository**.

You now have your own copy. Everything below happens in your copy.

### Step 3. Make a Gmail App Password

An App Password is a 16 letter code that lets this program send email from your Gmail without knowing your real password. You can delete it any time.

1. Sign in to the Gmail account that will **send** the alerts.
2. Go to https://myaccount.google.com/security and turn on **2-Step Verification** if it is off. Google requires this before it will give you an App Password.
3. Go to https://myaccount.google.com/apppasswords
4. Type a name such as `job alerts` and click **Create**.
5. Google shows a 16 letter code. Copy it now. You will not be able to see it again. Spaces in it do not matter.

### Step 4 (optional). Get an Anthropic API key for the AI filter

You can skip this step. Without a key, the alerts still work and use keyword matching only. With a key, a small AI model reads each match and removes the ones that are clearly not what you want, so you get fewer false alarms. See "API cost" below before you decide.

1. Go to https://console.anthropic.com and create an account.
2. Add a small amount of credit, for example 5 US dollars. Leave **automatic reload switched off**.
3. Open **API keys**, click **Create key**, and copy the key. It starts with `sk-ant-`.

### Step 5. Add your secrets to GitHub

Secrets are private settings that only your copy can read. Nobody can see them after you save them.

1. In your copy on GitHub, click **Settings** (top row of tabs).
2. In the left menu, click **Secrets and variables**, then **Actions**.
3. Click **New repository secret**. Add these one at a time. The name must match exactly, in capital letters.

| Name | What to paste |
| --- | --- |
| `EMAIL_ADDRESS` | The Gmail address that sends the alerts |
| `EMAIL_APP_PASSWORD` | The 16 letter App Password from step 3 |
| `RECIPIENT_EMAIL` | The address that should receive the alerts |
| `ANTHROPIC_API_KEY` | Optional. The key from step 4. Skip this row if you skipped step 4 |

### Step 6. Pick finance or tech

1. In your copy, click the file **config.yaml**.
2. Click the pencil icon (Edit this file) at the top right of the file.
3. Near the top you will see this line:

   `preset: finance`

   Change `finance` to `tech` if you want the tech version. Otherwise leave it.
4. Also find `years: [2027]` and `grad_year: 2029`. Change them to match you. For example, if you want jobs that mention 2026 or 2027, write `years: [2026, 2027]`.
5. Click **Commit changes**, then **Commit changes** again in the box that appears.

### Step 7. Turn on Actions

GitHub switches automatic tasks off in new copies until you agree.

1. Click the **Actions** tab at the top of your copy.
2. If you see a green button saying **I understand my workflows, go ahead and enable them**, click it.

### Step 8. Run it once by hand

1. Click the **Actions** tab.
2. In the left list, click **Job alerts**.
3. Click **Run workflow** on the right, then the green **Run workflow** button.
4. Wait a few seconds, then refresh the page. A yellow dot means it is running.

The first run reads every posting at every company, so it takes a few minutes. After that, each run only looks at what is new.

**What the first run does:** it does **not** email you everything that is open today. It quietly remembers every current posting, then sends you **one short email** saying setup worked. From then on, you only get an email when a new matching posting appears. If you would rather get the full list of everything open right now on the first run, open `config.yaml` and change `send_backlog_on_first_run: false` to `true` before you run it. That first email can be very long (about 850 jobs in testing without the AI filter, sent as around 9 emails).

From now on it runs by itself every 3 hours.

---

## How to tell it is working

* On the **Actions** tab, the latest run has a **green check**. A red cross means something went wrong, see Troubleshooting.
* Click the run, then **run**, then **Look for new jobs and send the email**. Near the bottom you will see a line like `Sent: 23 new jobs matching your alerts`. If you see `Nothing new, no email sent`, then nothing new was found, which is normal on most runs.
* Check your inbox (and your spam folder the first time). After the first run you should have one email called **Job alerts are set up and working**. Mark it **Not spam** so later alerts reach your inbox. Job emails only arrive after that, when something new is posted. Most runs find nothing new and send nothing.
* In your copy, click the branch menu near the top left. You will see a second branch called **state**. That is where the program saves its memory of which jobs it has already emailed, so you never get the same job twice. Leave it alone.

To test just the email part, you can ask for a short test message: on your own computer run `python run.py --test-email`. Most people do not need this.

---

## Finance version: what it covers

The finance version searches for these kinds of internships and co-ops:

investment banking, sales and trading, equity research, asset management, risk, corporate finance, capital markets, wealth management, accounting and audit, and finance or business analyst roles. It also catches the words banks use for student programs, such as summer analyst, summer associate, spring week, insight programme, co-op, and the French word stagiaire.

Companies it checks (around 100):

* **Canadian banks:** RBC, TD, CIBC, BMO, Desjardins, Scotiabank, National Bank.
* **Insurers:** Sun Life, Canada Life, MetLife Investment Management, Prudential, AIG, Allstate, Travelers, MassMutual, Marsh McLennan.
* **Pension funds and large investors:** CPP Investments, OMERS, PSP Investments, BCI, CDPQ, AIMCo, UVIMCO, TIAA, Brookfield.
* **Asset managers:** Fidelity, BlackRock, Vanguard, State Street, T. Rowe Price, Neuberger Berman, Invesco, Wellington, Northern Trust, Blackstone, Carlyle, Oaktree, AQR, Man Group, StepStone, Artisan, Cohen & Steers, Harris Associates, Ameriprise, Raymond James, Morningstar, and more.
* **Large banks:** Morgan Stanley, Citi, Wells Fargo, PNC, Truist, U.S. Bank, Capital One, Barclays, Deutsche Bank.
* **Advisory and boutique banks:** William Blair, LionTree, Ducera, Lincoln International, D.A. Davidson, B. Riley.
* **Trading and quant firms:** Jane Street, Point72, Akuna, Tower, Jump, Virtu, Flow Traders, Squarepoint, Qube, WorldQuant, Schonfeld, and others.
* **Accounting:** PwC campus roles, BDO, RSM, Forvis Mazars, Schneider Downs, Frazier & Deeter, Moore Colson.

Every one of these career sites was checked and returned jobs when this was set up. The full list is in `config.yaml`.

**Not covered:** Manulife, Ontario Teachers' Pension Plan and iA Financial. No public job list that this program can read was found for them, so check their career pages yourself. Some other big names, such as Goldman Sachs, JPMorgan, Bank of America, UBS, Lazard and Evercore, are not in the list because no readable job list was verified for them. You can add any company (see "Changing settings").

### Alerts are the main value, not auto-apply

Most banks take applications through a system called **Workday**. Workday needs an account for every company and long, multi-page forms, so a program cannot safely fill it in for you. This project reads the Workday job lists to **tell you the moment a job appears**, and you apply yourself. For banking, being among the first to apply matters, so a fast alert is the useful part.

An optional auto-apply feature exists, but it only works for a few other systems (Greenhouse, Lever, Ashby), it is off by default, and most finance students will not need it. See `docs/AUTO_APPLY.md`.

---

## API cost (only if you use the AI filter)

The AI filter uses Anthropic's smallest model, Claude Haiku 4.5. At the time of writing it costs 1 US dollar per million input tokens and 5 US dollars per million output tokens. Check https://www.anthropic.com/pricing for the current prices.

* Only jobs that already pass the free keyword filter are sent to the AI.
* One job costs roughly a quarter of a US cent.
* The first run makes no AI calls at all, because it only remembers what is already open. It costs nothing.
* After that, only new jobs that pass the keyword filter are checked, usually pennies per week.

**Keep auto-reload off.** In the Anthropic Console, open the billing page, buy a small prepaid amount (5 US dollars lasts a long time), and make sure automatic reload is switched off. Then the most you can ever spend is what you put in. If the credit runs out, nothing breaks. The alerts keep arriving using keyword matching only.

GitHub also has a free monthly allowance of automatic run time for private copies. This project runs for a few minutes every 3 hours, which fits inside it. If you want to use less, open `.github/workflows/alerts.yml` and change `*/3` to `*/6` to run every 6 hours.

---

## Changing settings

Everything is in `config.yaml`, with notes next to each setting. Edit it on GitHub with the pencil icon, as in step 6.

* **Years:** `years: [2027]`.
* **Role words:** under your preset, the `roles` list. Add a line such as `- credit analyst`.
* **Companies:** under `companies`. For a company on Greenhouse, Lever or Ashby, add a line like `- {name: Acme Capital, slug: acmecapital}`. The slug is the last part of the company's job board address, for example `boards.greenhouse.io/acmecapital`.
* **Timezone:** `timezone: America/Toronto`.
* **Turn AI filter off:** `llm: enabled: false`.

After you add a company, check it works. On your own computer, run `python verify_boards.py`. It lists every company and how many jobs it found.

---

## Troubleshooting

**I got no email.**
Check your spam folder. Then open the latest run in the Actions tab and read the last lines. If it says `Nothing new, no email sent`, there were no new matches. If it shows an error, find it below.

**Red cross, and the message says "Missing secret(s)".**
One of the secrets from step 5 is missing or misspelled. The names must match exactly, in capitals.

**Red cross, and the message says "Gmail rejected the login".**
Use the 16 letter App Password from step 3, not your normal Gmail password. Make sure `EMAIL_ADDRESS` is the same Gmail account that created it, and that 2-Step Verification is on.

**Red cross, and a message about "permission" or "403" near the end.**
The program could not save its memory. The workflow file already asks for write access, so this should be rare, but some accounts or organizations block it. Click **Settings**, then **Actions**, then **General** in the left menu. Scroll to **Workflow permissions**, choose **Read and write permissions**, click **Save**, then run it again.

**Red cross, and the message says "Config problem".**
You made a typing mistake in `config.yaml`. The message shows roughly where. Spaces at the start of lines matter, and every `[` needs a closing `]`. If you get stuck, copy the file again from the original project and start over.

**It never runs by itself.**
GitHub can start scheduled runs up to an hour late. Also confirm you did step 7. You can always press **Run workflow** by hand.

**I get the same job twice.**
Check the **Actions** tab for red crosses on the **Save the list of jobs already seen** step. If it failed, the program could not save its memory, so fix the permission as described above. It can also happen when a company lists the same job under two different titles.

**I get too many jobs I do not want.**
Add your Anthropic key (steps 4 and 5). Without it, expect some jobs that are not finance, such as IT or engineering internships at banks and consulting roles. You can also remove broad words from the `roles` list in `config.yaml`, such as `finance` or `risk`, or list overseas cities under `exclude_locations`.

**I got the setup email but never get any job emails.**
Runs that find nothing new send no email. Open the latest run on the **Actions** tab and read the line that starts with `Scanned`. If it says `0 unseen postings` for several days, check `years` and the `roles` list in `config.yaml`. New student postings are often rare outside the autumn recruiting season.

**I get too few jobs.**
Check the `years` line matches the year in the postings. Remember that many companies only post summer roles in the autumn. Add `2026` to the years if you also want this year's co-ops.

**I only got one short email and no jobs.**
That is the first-run setup email, and it is working as designed. Jobs that were already open were remembered so they do not flood your inbox. You will get emails when new ones appear. If you want the full list of everything open today, set `send_backlog_on_first_run: true` in `config.yaml`, then delete the `state` branch (Code tab, branch menu, **View all branches**, trash icon next to `state`) and run the workflow again.

**A company shows an error in the log.**
Companies sometimes move their career site. The program skips that company and tries again next time, and every other company still works. Run `python verify_boards.py` to see which ones are broken.

---

## Safety and privacy

* Keep your copy **private**.
* Never paste a password or key into any file. Secrets belong only in Settings, Secrets and variables, Actions.
* You can delete the App Password at https://myaccount.google.com/apppasswords at any time, and delete the Anthropic key in the Console. Do that if you ever think either leaked.
* The program only reads public career pages. It does not log in anywhere or apply to anything unless you turn on the optional auto-apply.

---

## For developers

```bash
pip install -r requirements.txt
cp .env.example .env        # fill in the values
python run.py --dry-run     # scan and print what would be emailed, send nothing
python run.py               # scan and email
python verify_boards.py     # check every company in config.yaml returns jobs
python -m unittest discover tests
```

Layout: `jobalert/` is the alert pipeline (sources, keyword filter, optional AI filter, email, memory). `autoapply/` is the optional auto-apply and dashboard code. MIT licensed, see `LICENSE`.
