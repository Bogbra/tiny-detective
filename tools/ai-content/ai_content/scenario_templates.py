"""Data-only library of cozy, family-friendly scenario templates for the
deterministic case-logic builder (see logic_builder.py).

Each template supplies everything the deterministic layer needs to construct
a guaranteed-solvable puzzle WITHOUT any LLM call: a setting/problem pair, an
incident location, two alternative "alibi" locations, and three roles each
bound to a "signature item" — a possession or trait unique to that role.

The signature item is what makes the identifying clue robust: whichever role
ends up being the culprit (randomized per generation, not fixed here), the
identifying clue anchors on that role's signature item, which is known
deterministically before any prose is written. This avoids depending on an
LLM-invented detail (like a name-initial) ever being echoed back correctly —
see logic_builder.py and ADR-0007's redesign addendum for the full reasoning.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScenarioTemplate:
    key: str
    setting_sentence: str
    problem_sentence: str
    missing_item: str
    incident_location: str
    alibi_locations: tuple[str, str]
    roles: tuple[str, str, str]
    signature_items: tuple[str, str, str]  # index-matched with roles
    neutral_clue: str


SCENARIO_TEMPLATES: tuple[ScenarioTemplate, ...] = (
    ScenarioTemplate(
        key="bake_sale",
        setting_sentence="A cozy neighborhood bake sale on a sunny Saturday morning.",
        problem_sentence="The prize-winning strawberry pie has vanished from the dessert table.",
        missing_item="strawberry pie",
        incident_location="the dessert table",
        alibi_locations=("the entrance", "the coin box"),
        roles=("Student Helper", "Class Treasurer", "Poster Designer"),
        signature_items=(
            "a stack of napkins with a torn corner",
            "a small ledger notebook",
            "a paint-stained sketchbook",
        ),
        neutral_clue="A gentle breeze kept knocking over the paper table signs all morning.",
    ),
    ScenarioTemplate(
        key="museum",
        setting_sentence="A small town museum just after closing time.",
        problem_sentence="An old display key has disappeared from its locked glass case.",
        missing_item="display key",
        incident_location="the display case",
        alibi_locations=("the archive room", "the east hallway"),
        roles=("Curator", "Night Guard", "Visitor"),
        signature_items=(
            "a clipboard with an inventory checklist",
            "a heavy keyring with a flashlight attached",
            "a crumpled museum ticket stub",
        ),
        neutral_clue="The gift shop lights had been left on since the afternoon.",
    ),
    ScenarioTemplate(
        key="library",
        setting_sentence="A quiet neighborhood library on a rainy afternoon.",
        problem_sentence="A rare first-edition bookmark has gone missing from the reading nook.",
        missing_item="first-edition bookmark",
        incident_location="the reading nook",
        alibi_locations=("the front desk", "the children's section"),
        roles=("Librarian", "Book Club Member", "Student"),
        signature_items=(
            "a stamp pad with red ink smudges",
            "a knitted tote bag with loose yarn",
            "a highlighter-stained notebook",
        ),
        neutral_clue="Rain kept dripping steadily from a leaky window near the entrance.",
    ),
    ScenarioTemplate(
        key="art_class",
        setting_sentence="A community center art class on a weekday evening.",
        problem_sentence="Someone's prized set of watercolor brushes is missing from the supply table.",
        missing_item="watercolor brushes",
        incident_location="the supply table",
        alibi_locations=("the sink area", "the easel corner"),
        roles=("Instructor", "New Student", "Class Regular"),
        signature_items=(
            "a smock with dried blue paint streaks",
            "a half-finished sketch signed with a small doodle",
            "a jar of cloudy rinse water",
        ),
        neutral_clue="Someone had left the window cracked open, letting in the evening air.",
    ),
    ScenarioTemplate(
        key="science_fair",
        setting_sentence="A school science fair set up in the gymnasium.",
        problem_sentence="A student's award ribbon has disappeared from the judging table.",
        missing_item="award ribbon",
        incident_location="the judging table",
        alibi_locations=("the volcano display", "the registration table"),
        roles=("Judge", "Participant", "Volunteer"),
        signature_items=(
            "a clipboard with a scoring rubric",
            "a poster board with a torn corner",
            "a name-tag lanyard with a spare battery clipped to it",
        ),
        neutral_clue="The gym's overhead fan rattled loudly throughout the afternoon.",
    ),
    ScenarioTemplate(
        key="birthday_party",
        setting_sentence="A backyard birthday party on a warm afternoon.",
        problem_sentence="The last slice of chocolate cake has gone missing from the snack table.",
        missing_item="chocolate cake",
        incident_location="the snack table",
        alibi_locations=("the game corner", "the gift table"),
        roles=("Party Host", "Cousin", "Family Friend"),
        signature_items=(
            "a striped party hat with a bent elastic band",
            "a half-inflated balloon animal",
            "a camera with a wrist strap",
        ),
        neutral_clue="A wobbly folding chair kept tipping over near the patio door.",
    ),
)
