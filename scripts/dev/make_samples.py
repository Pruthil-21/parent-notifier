"""Write the fictional sample sheets in samples/, used by `flask seed-demo`.

Every name and number here is made up; phones run from +91 90000 00101 upward. The
numbers are worked out from each student's position, so the files come out the same
every run and cover every case: attendance shortages, failed and absent Mid-Sems,
theory-only subjects and a Mid-Sem not yet held. Run with:

    uv run python scripts/dev/make_samples.py
"""

from pathlib import Path

from openpyxl import Workbook

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
FIRST_NAMES = [
    "Aarav",
    "Diya",
    "Kabir",
    "Isha",
    "Vihaan",
    "Anaya",
    "Reyansh",
    "Myra",
    "Arjun",
    "Saanvi",
    "Dhruv",
    "Kiara",
    "Parth",
    "Riya",
    "Yash",
    "Tanvi",
    "Neel",
    "Zoya",
    "Om",
    "Pari",
]
SURNAMES = ["Shah", "Patel", "Desai", "Mehta", "Joshi", "Trivedi", "Bhatt", "Parikh"]
PARENTS = ["Mehul", "Kiran", "Nilesh", "Hetal", "Rakesh", "Sonal", "Jignesh", "Bhavna"]
# (subject, has practical, Mid-Sem held yet)
SUBJECTS = {
    6: [
        ("Compiler Design", True, True),
        ("Computer Networks", True, True),
        ("Software Engineering", False, True),
        ("Machine Learning", True, True),
    ],
    7: [
        ("Cloud Computing", True, True),
        ("Information Security", True, True),
        ("Big Data Analytics", True, False),
        ("Professional Ethics", False, False),
    ],
}


def _cell(student: int, subject: int, semester: int, practical: bool, midsem: bool) -> str:
    parts = [f"Theory={66 + (student * 7 + subject * 11 + semester) % 34}"]
    if practical:
        parts.append(f"Practical={70 + (student * 5 + subject * 3 + semester) % 30}")
    if midsem:
        absent = (student + subject * 3 + semester) % 17 == 0
        parts.append("Marks=AB" if absent else f"Marks={4 + (student * 3 + subject * 5) % 17}")
    return ",".join(parts)


def write_sheet(semester: int) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append([f"GCET Computer Engineering CE-A, Sem {semester} attendance and Mid-Sem"])
    sheet.append([])
    subjects = SUBJECTS[semester]
    sheet.append(
        [
            "Sr No",
            "Enrollment No",
            "Student Name",
            "Parent Name",
            "Parent Phone",
            *(name for name, _, _ in subjects),
        ]
    )
    for index, first in enumerate(FIRST_NAMES):
        surname = SURNAMES[index % len(SURNAMES)]
        cells = [
            _cell(index, number, semester, practical, midsem)
            for number, (_, practical, midsem) in enumerate(subjects)
        ]
        sheet.append(
            [
                index + 1,
                f"2301201070{index + 1:02}",
                f"{first} {surname}",
                f"{PARENTS[index % len(PARENTS)]} {surname}",
                f"90000 00{101 + index}",
                *cells,
            ]
        )
    path = SAMPLES / f"ce-a-sem-{semester}.xlsx"
    workbook.save(path)
    return path


if __name__ == "__main__":
    SAMPLES.mkdir(exist_ok=True)
    for number in SUBJECTS:
        print(f"Wrote {write_sheet(number).relative_to(SAMPLES.parent)}")
