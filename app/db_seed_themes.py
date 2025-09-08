from sqlalchemy.orm import Session

from app.models.event import Theme
from db import SessionLocal


def upsert_theme(db: Session, spec: dict):
    name = spec.get("Name")
    row = db.query(Theme).filter(Theme.Name == name).first()
    if not row:
        row = Theme(Name=name)
        db.add(row)
    # Set/update fields
    for k in [
        "Description",
        "ButtonColour1",
        "ButtonColour2",
        "ButtonStyle",
        "BackgroundColour",
        "BackgroundImage",
        "CoverPhotoPath",
        "FontFamily",
        "TextColour",
        "AccentColour",
        "InputBackgroundColour",
        "DropzoneBackgroundColour",
    ]:
        if k in spec:
            setattr(row, k, spec[k])
    db.commit()


def seed_themes():
    db: Session = SessionLocal()
    themes = [
        Theme(
            Name="Classic Light",
            Description="Clean white page with dark text; high-contrast coral→amber buttons.",
            ButtonColour1="#e14b3f",  # slightly darker coral for contrast
            ButtonColour2="#f28a02",  # amber-600
            ButtonStyle="gradient",
            BackgroundColour="#ffffff",
            FontFamily="Inter, Arial, sans-serif",
            TextColour="#0f172a",  # slate-900
            AccentColour="#D0D7DE",  # subtle gray border on light
            InputBackgroundColour="#f3f4f6",
            DropzoneBackgroundColour="#f8fafc",
        ),
        Theme(
            Name="Midnight",
            Description="True dark page, light text; vivid blue→violet buttons.",
            ButtonColour1="#3b82f6",  # blue-500
            ButtonColour2="#7c3aed",  # violet-600
            ButtonStyle="gradient",
            BackgroundColour="#0b0b10",
            FontFamily="Inter, Arial, sans-serif",
            TextColour="#e9eef6",
            AccentColour="rgba(255,255,255,0.18)",
            InputBackgroundColour="#15161e",
            DropzoneBackgroundColour="#121424",
        ),
        Theme(
            Name="Emerald",
            Description="Soft green page; dark text; deep green→teal buttons for contrast.",
            ButtonColour1="#1f7a5c",  # deep emerald
            ButtonColour2="#0b4f49",  # teal-900ish
            ButtonStyle="solid",
            BackgroundColour="#e8f5e9",  # green-50
            FontFamily="Inter, Arial, sans-serif",
            TextColour="#111827",
            AccentColour="#C8E6C9",  # muted green border on light
            InputBackgroundColour="#f1f8f4",
            DropzoneBackgroundColour="#ecfdf5",
        ),
        Theme(
            Name="Sunset",
            Description="Warm peach page; readable dark text; orange→rose buttons.",
            ButtonColour1="#f59e0b",  # amber-500
            ButtonColour2="#e11d48",  # rose-600
            ButtonStyle="gradient",
            BackgroundColour="#ffe7da",
            FontFamily="Inter, Arial, sans-serif",
            TextColour="#1f2937",
            AccentColour="#F8DAD0",
            InputBackgroundColour="#fff3ef",
            DropzoneBackgroundColour="#fff7ed",
        ),
        Theme(
            Name="Ocean",
            Description="Cool blue page; dark text; strong blue→cyan buttons.",
            ButtonColour1="#2563eb",  # blue-600
            ButtonColour2="#06b6d4",  # cyan-500
            ButtonStyle="gradient",
            BackgroundColour="#e3f2fd",
            FontFamily="Inter, Arial, sans-serif",
            TextColour="#0f172a",
            AccentColour="#C9E6FF",
            InputBackgroundColour="#eef6ff",
            DropzoneBackgroundColour="#e3f2fd",
        ),
        Theme(
            Name="Lavender",
            Description="Soft lavender page; dark text; violet→plum buttons with contrast.",
            ButtonColour1="#7c3aed",  # violet-600
            ButtonColour2="#9333ea",  # violet-600/700
            ButtonStyle="gradient",
            BackgroundColour="#f3e8ff",
            FontFamily="Inter, Arial, sans-serif",
            TextColour="#1f2937",
            AccentColour="#E9D5FF",
            InputBackgroundColour="#faf5ff",
            DropzoneBackgroundColour="#f3e8ff",
        ),
        Theme(
            Name="High Contrast",
            Description="Strict black/white page; solid black buttons by default.",
            ButtonColour1="#111111",
            ButtonColour2="#111111",
            ButtonStyle="solid",
            BackgroundColour="#ffffff",
            FontFamily="Inter, Arial, sans-serif",
            TextColour="#000000",
            AccentColour="#2A2E3F",
            InputBackgroundColour="#f3f4f6",
            DropzoneBackgroundColour="#f8fafc",
        ),
        # Examples-inspired presets
        Theme(
            Name="Wedding Elegant",
            Description="Soft neutral page; readable dark text; rose→light rose buttons.",
            ButtonColour1="#e6a4b4",
            ButtonColour2="#f5d7db",
            ButtonStyle="gradient",
            BackgroundColour="#fff8f7",
            FontFamily="Inter, Arial, sans-serif",
            TextColour="#2b2b2b",
            AccentColour="#F2E8E8",
            InputBackgroundColour="#fffaf9",
            DropzoneBackgroundColour="#fff1f2",
        ),
        Theme(
            Name="Corporate Sleek",
            Description="Professional light gray page; dark text; blue→sky buttons.",
            ButtonColour1="#2563eb",
            ButtonColour2="#0ea5e9",
            ButtonStyle="gradient",
            BackgroundColour="#f3f4f6",
            FontFamily="Inter, Arial, sans-serif",
            TextColour="#111827",
            AccentColour="#E5E7EB",
            InputBackgroundColour="#f7f7f8",
            DropzoneBackgroundColour="#eef2f7",
        ),
        Theme(
            Name="School Spirit",
            Description="Vibrant warm page; strong amber→red buttons; dark text.",
            ButtonColour1="#f59e0b",
            ButtonColour2="#ef4444",
            ButtonStyle="gradient",
            BackgroundColour="#fff7ed",
            FontFamily="Inter, Arial, sans-serif",
            TextColour="#1f2937",
            AccentColour="#FFEAD0",
            InputBackgroundColour="#fff3e6",
            DropzoneBackgroundColour="#fff7ed",
        ),
        Theme(
            Name="Sports Arena",
            Description="Energetic green page; readable slate text; green→emerald buttons.",
            ButtonColour1="#16a34a",
            ButtonColour2="#065f46",
            ButtonStyle="gradient",
            BackgroundColour="#ecfdf5",
            FontFamily="Inter, Arial, sans-serif",
            TextColour="#0f172a",
            AccentColour="#BBF7D0",
            InputBackgroundColour="#f0fdf4",
            DropzoneBackgroundColour="#ecfdf5",
        ),
        Theme(
            Name="Conference Modern",
            Description="Modern dark page; violet→cyan buttons; light text and subtle borders.",
            ButtonColour1="#7c3aed",
            ButtonColour2="#06b6d4",
            ButtonStyle="gradient",
            BackgroundColour="#0f0e17",
            FontFamily="Inter, Arial, sans-serif",
            TextColour="#fffffe",
            AccentColour="rgba(255,255,255,0.18)",
            InputBackgroundColour="#15161e",
            DropzoneBackgroundColour="#121424",
        ),
        Theme(
            Name="Community Festive",
            Description="Warm rosy page; orange→rose buttons; readable dark text.",
            ButtonColour1="#fb923c",
            ButtonColour2="#f43f5e",
            ButtonStyle="gradient",
            BackgroundColour="#fff1f2",
            FontFamily="Inter, Arial, sans-serif",
            TextColour="#1f2937",
            AccentColour="#FEE2E2",
            InputBackgroundColour="#fff7f9",
            DropzoneBackgroundColour="#fff1f2",
        ),
        Theme(
            Name="Slate Neon",
            Description="Dark slate card with neon cyan solid buttons.",
            ButtonColour1="#06b6d4",
            ButtonColour2="#06b6d4",
            ButtonStyle="solid",
            BackgroundColour="#0b0b10",
            FontFamily="Inter, Arial, sans-serif",
            TextColour="#e9eef6",
            AccentColour="rgba(255,255,255,0.18)",
            InputBackgroundColour="#15161e",
            DropzoneBackgroundColour="#121424",
        ),
    ]
    for t in themes:
        spec = {
            "Name": t.Name,
            "Description": t.Description,
            "ButtonColour1": t.ButtonColour1,
            "ButtonColour2": t.ButtonColour2,
            "ButtonStyle": t.ButtonStyle,
            "BackgroundColour": t.BackgroundColour,
            "BackgroundImage": t.BackgroundImage,
            "CoverPhotoPath": t.CoverPhotoPath,
            "FontFamily": t.FontFamily,
            "TextColour": t.TextColour,
            "AccentColour": t.AccentColour,
            "InputBackgroundColour": t.InputBackgroundColour,
            "DropzoneBackgroundColour": t.DropzoneBackgroundColour,
        }
        upsert_theme(db, spec)
    db.close()


if __name__ == "__main__":
    seed_themes()
