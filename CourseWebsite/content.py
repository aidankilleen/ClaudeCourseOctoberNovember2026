"""All of the editable text for the website lives in this file.

Change anything below and refresh the page in your browser - you never need to
touch the HTML. Keep the quotes and commas where they are and you'll be fine.
"""

# --- Company details (used in the header and the footer) ---------------------
# There is deliberately no year here: the copyright year in the footer is taken
# from today's date in app.py, so it can never go out of date.
COMPANY = {
    "name": "Professional Training",
    "tagline": "Practical skills training for growing teams",
}

# --- Navigation links in the header -----------------------------------------
# "href" must match the id of a section further down the page.
NAV = [
    {"label": "About", "href": "#about"},
    {"label": "Courses", "href": "#courses"},
    {"label": "Why Us", "href": "#why-us"},
    {"label": "Testimonials", "href": "#testimonials"},
    {"label": "Contact", "href": "#contact"},
]

# --- The big banner at the top of the page ----------------------------------
HERO = {
    # A short promotional line shown as a badge above the headline. To take the
    # offer down, delete this line - the badge disappears and nothing else moves.
    "offer": "Back to school offer - all courses reduced by 10%",
    "headline": "Training that your team will actually use on Monday morning",
    "tagline": (
        "Hands-on, instructor-led courses in leadership, project delivery and "
        "everyday workplace skills - delivered on site or online."
    ),
    "button_label": "Contact Us",
    "button_href": "#contact",
}

# --- About Us ----------------------------------------------------------------
ABOUT = {
    "heading": "About Us",
    "paragraph": (
        "Professional Training has been helping organisations build capable, "
        "confident teams since 2009. We are a small group of experienced "
        "practitioners - not career lecturers - and every course we run is "
        "built around the real problems our clients bring us. We work with "
        "companies of every size, from ten-person studios to national "
        "employers, and we tailor each programme to the people in the room "
        "rather than reading from a fixed script."
    ),
}

# --- Courses -----------------------------------------------------------------
# Add or remove courses here; the page updates automatically.
COURSES = [
    {
        "title": "Leadership Essentials",
        "description": (
            "For new and recently promoted managers. Covers delegation, "
            "giving feedback that lands, and handling difficult conversations "
            "without losing the room."
        ),
        "duration": "2 days",
    },
    {
        "title": "Project Management Fundamentals",
        "description": (
            "Planning, scoping and tracking work that finishes on time. "
            "Practical tools you can apply to your next project, with no "
            "certification jargon."
        ),
        "duration": "3 days",
    },
    {
        "title": "Effective Communication at Work",
        "description": (
            "Write clearer emails, run shorter meetings and present ideas so "
            "that people remember them. Includes a recorded practice session "
            "with individual feedback."
        ),
        "duration": "1 day",
    },
    {
        "title": "Data Analysis with Excel",
        "description": (
            "Turn messy spreadsheets into reports people trust. Pivot tables, "
            "lookups, charts and the handful of formulas that do most of the "
            "work."
        ),
        "duration": "2 days",
    },
    {
        "title": "Customer Service Excellence",
        "description": (
            "Handle complaints calmly, recover unhappy customers and build "
            "the kind of service reputation that brings repeat business."
        ),
        "duration": "1 day",
    },
]

# --- Why Choose Us -----------------------------------------------------------
BENEFITS = [
    {
        "title": "Trainers who have done the job",
        "description": (
            "Every trainer has spent at least ten years doing the work they "
            "teach, so the examples come from real projects."
        ),
    },
    {
        "title": "Small groups",
        "description": (
            "We cap courses at twelve people. Everyone gets to ask their own "
            "questions and practise properly."
        ),
    },
    {
        "title": "Tailored to your organisation",
        "description": (
            "We talk to you before the course and rewrite the exercises to "
            "use your systems, your terminology and your challenges."
        ),
    },
    {
        "title": "Support after the course",
        "description": (
            "Delegates keep their workbook and can email their trainer with "
            "follow-up questions for three months afterwards."
        ),
    },
]

# --- Testimonials ------------------------------------------------------------
TESTIMONIALS = [
    {
        "quote": (
            "The leadership course changed how our team leads run their "
            "one-to-ones. Six months on, it has stuck - that almost never "
            "happens with training."
        ),
        "name": "Sarah Nolan",
        "role": "HR Director, Hartley Group",
    },
    {
        "quote": (
            "They rebuilt the whole project management course around our own "
            "delivery process. It felt like it was written for us, because it "
            "was."
        ),
        "name": "Michael Byrne",
        "role": "Operations Manager, Westline Logistics",
    },
    {
        "quote": (
            "Genuinely the first Excel course where nobody in the room looked "
            "bored. Our monthly reporting takes half the time it used to."
        ),
        "name": "Aoife Kelly",
        "role": "Finance Lead, Brightpath Services",
    },
]

# --- Contact details ---------------------------------------------------------
CONTACT = {
    "heading": "Contact",
    "intro": (
        "Tell us what your team needs and we will send back an outline and a "
        "price within two working days."
    ),
    "email": "info@professional.ie",
    "phone": "+353 1 555 0147",
    "address": "24 Merchants Quay, Dublin 8, D08 XY12, Ireland",
}
