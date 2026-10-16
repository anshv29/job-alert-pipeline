# Auto-apply and dashboard (optional, off by default)

Most people should skip this page. The job alerts work on their own and need no database.

Auto-apply fills in application forms **on your own computer** for jobs that pass a set of safety rules. It only handles jobs on **Greenhouse, Lever and Ashby**. Most banks use Workday, which this does not handle, so for finance the alerts are the main value.

## What you need

* A free Supabase account (a database). Alerts do not need this, only auto-apply does.
* A Mac or PC that stays on while it runs.
* Python 3.9 or newer.

## Setup

1. Install the extra packages:

   ```bash
   pip install -r requirements-autoapply.txt
   playwright install chromium
   ```

2. Create a Supabase project and copy its **Session pooler** connection string. Put it in your `.env` file as `DATABASE_URL=...` and also add it as a GitHub secret named `DATABASE_URL`.
3. Create the table once: `python -m autoapply.db`.
4. Make a folder called `private/` (it is never uploaded). Put your resume there as `private/resume.pdf`. Copy `answers.example.yaml` to `private/answers.yaml` and fill in your own details.
5. In `config.yaml` set `features: auto_apply: true`. Set your real `grad_year`.
6. Run the alerts so jobs are saved: `python run.py`.

## Try it safely

`DRY_RUN` is on unless you write `DRY_RUN=false` in `.env`. A dry run fills in a form and takes a screenshot but never clicks submit and never writes to the database.

```bash
python -m autoapply.applier --limit 3
python -m autoapply.applier --test-url "https://job-boards.greenhouse.io/company/jobs/123"
```

Look at the screenshots in `private/screenshots`. Only set `DRY_RUN=false` once you are happy.

## Safety rules built in

* Applies only to jobs the AI marked as a good fit, in the categories under `auto_apply_domains` for your preset.
* Skips companies in the preset's `blocklist`.
* Skips jobs that ask for a graduation year or year of study that does not fit you.
* Anything unclear goes to `needs_review` instead of being applied to.
* Never answers a question that is not in your `answers.yaml`. Required essay questions are drafted for you to edit and are never sent.
* Stops on any CAPTCHA.
* At most `daily_cap` applications a day (default 10), with a random pause between them.
* Turn everything off by setting `features: auto_apply: false`.

The AI filter must be on (an Anthropic key) for auto-apply to mark any job as eligible. Without it, every job goes to `needs_review`.

## Dashboard

A nightly email summary of what auto-apply did. Set `features: dashboard: true` and `auto_apply: true`, then follow the comment at the top of `.github/workflows/dashboard.yml`. Test it with `python -m autoapply.dashboard --force`.
