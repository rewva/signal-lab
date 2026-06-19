# Connecting your accounts (one-time live setup)

After this, **Approve** in the review queue posts automatically. Everything here uses *your own*
YouTube/FB/IG accounts; no Meta App Review is needed while the app holds Standard Access for
role-holder accounts (see `docs/posting-pipeline-api-research.md`).

Prereqts already done: ffmpeg installed; publisher runs via `python -m publisher`.

---

## 1. YouTube (Google Cloud OAuth)

In the browser (your Google account that owns the channel):

1. https://console.cloud.google.com/ -> create a project (e.g. `daily-gk-quiz`).
2. **APIs & Services -> Library -> YouTube Data API v3 -> Enable.**
3. **OAuth consent screen:** User type = External; fill app name + your email; add yourself under
   **Test users** (keeps you out of the verification/review requirement).
4. **Credentials -> Create credentials -> OAuth client ID -> Application type: Desktop app.**
   Copy the **Client ID** and **Client secret**.

Then, in this folder, with the publisher running:

```powershell
$env:PUBLISHER_GOOGLE_CLIENT_ID = "<client id>"
$env:PUBLISHER_GOOGLE_CLIENT_SECRET = "<client secret>"
python -m publisher.connect youtube --brand daily-gk-quiz --account-id "<your channel handle>"
```

A browser opens -> pick the channel's Google account -> allow. The helper stores the refresh
token in the vault under `daily-gk-quiz:youtube`.

> Put the same two `PUBLISHER_GOOGLE_*` values in a `.env` here (or the environment) so the
> running server can refresh the token at posting time.

---

## 2. Facebook Page + Instagram (Meta)

Precondition: your **FB Page** exists and an **IG Business/Creator** account is linked to it
(Page -> Settings -> Linked accounts), and you are a role-holder on both.

1. https://developers.facebook.com/ -> **My Apps -> Create App -> Business.** Note the
   **App ID** and **App Secret** (Settings -> Basic).
2. Add **role-holders**: App Roles -> add your FB account; ensure the Page + IG are yours.
3. **Graph API Explorer** (https://developers.facebook.com/tools/explorer/): select your app,
   **Generate Access Token** with permissions: `pages_show_list`, `pages_read_engagement`,
   `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`,
   `business_management`. Copy the (short-lived) **User token**.

Then, with the publisher running:

```powershell
python -m publisher.connect meta --brand daily-gk-quiz `
  --user-token "<short-lived user token>" `
  --app-id "<app id>" --app-secret "<app secret>"
```

The helper exchanges it for a **long-lived Page token**, picks your Page (pass `--page "<name or
id>"` if you have several), discovers the linked IG business account, and stores both
`daily-gk-quiz:facebook` and `daily-gk-quiz:instagram` credentials in the vault.

---

## 3. Posting windows (when approved videos go out)

Approve schedules a job into the next free per-account window (or "now" if none are set). Set one
window per account, e.g. daily 18:30 (days 0=Mon..6=Sun):

```powershell
# find the account ids
curl http://127.0.0.1:8077/api/accounts
# add a window (repeat per account id)
curl -X POST http://127.0.0.1:8077/api/accounts/1/windows `
  -H "Content-Type: application/json" -d '{\"time_slot\":\"18:30\",\"days_of_week\":[0,1,2,3,4,5,6]}'
```

---

## 4. Verify

```powershell
curl http://127.0.0.1:8077/api/accounts   # should list youtube/facebook/instagram, token_broken=false
```

Now Approve a video in the review queue (`/`): it goes APPROVED -> SCHEDULED, the scheduler tick
picks it up at its window, the orchestrator normalizes (ffmpeg) and posts to all three platforms.
