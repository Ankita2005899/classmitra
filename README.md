# ClassMitra

AI classroom assistant. The dashboard drills down **Department > Class > Division > Subject**, and each subject opens the lesson studio and live classroom.

## Pages

| File | What it is |
|---|---|
| `index.html` | Dashboard (departments, classes, divisions, subjects) |
| `studio.html` | Lesson studio (text to teacher video) and live classroom (attention tracking) |
| `js/data.js` | Site name and **sample** departments, subjects, teachers. Replace with your own |
| `js/dashboard.js` | Dashboard logic |
| `js/app.js` | Lesson studio and live classroom logic (demo mode) |
| `css/style.css`, `css/dashboard.css` | Styles |

## Run it locally

```
python -m http.server 5500
```

Then open http://localhost:5500

## Connect a backend later

Set `API_BASE` at the top of `js/app.js`. The UI expects:

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | /api/lessons | topic, details, avatar, visuals, language | `{ scenes: [...], video_url }` |
| POST | /api/callout | student | ok |
| POST | /api/whatsapp | to, student | ok |
| POST | /api/youtube/upload | none | ok |

## Next steps

1. Attendance: live rotating code on the teacher's screen and a student check-in page.
2. PPT upload with per-slide scripts and student doubt answers.
3. FastAPI backend: LLM script, TTS, lip-sync avatar, FFmpeg.

Keep API keys in a backend `.env` file. Never put them in the JavaScript.
