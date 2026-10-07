# Approved campaign creative

Drop the supplied artwork here, using these exact filenames. The WhatsApp
message preview picks one per campaign objective (see components/wa-message.tsx).

| Filename | The image it should be | Used for |
|---|---|---|
| `consult-handover.png` | Two colleagues at a desk, one handing over documents, glass wall onto planting, plum logo bottom-left | Health checkup activation |
| `evening-call.png` | Desk phone by a window, city skyline at sunset | Telehealth activation |
| `rest-bench.png` | Two people sitting back on a bench under a tree in evening light | Cross-sell, app install, re-engagement |

Rules for this folder:

1. **Only supplied artwork goes here.** Never a redrawn or generated
   substitute. If the file is missing the preview renders a visible, labelled
   empty frame on purpose, because a stand-in that looks finished will be read
   as the approved asset in a demo or a screenshot.
2. `.png` is the expected extension. To use a different one, change the entry
   in `CREATIVE` in `components/wa-message.tsx` rather than renaming the file
   to something it is not.
3. These are marketing creative, not member data. Nothing here may contain a
   screenshot of real records, names, or claim detail.
