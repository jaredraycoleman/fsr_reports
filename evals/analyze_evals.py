#!/usr/bin/env python3
"""
Analyze course evaluations for 2025 FSR.
Processes CSV files from LMU course evaluations and extracts:
- Numerical ratings and statistics
- Positive feedback examples
- Areas for improvement
"""

import csv
import os
import re
import sys
from pathlib import Path
from collections import defaultdict
import statistics

# Fix encoding on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Rating mappings
LIKERT_MAP = {
    "Strongly Agree": 5,
    "Agree": 4,
    "Uncertain": 3,
    "Disagree": 2,
    "Strongly Disagree": 1,
}

EFFECTIVENESS_MAP = {
    "Excellent": 5,
    "Very Good": 4,
    "Good": 3,
    "Fair": 2,
    "Very Poor": 1,
}

# Question labels (shortened)
QUESTION_LABELS = {
    "Learning outcomes for the course were clearly stated": "Outcomes Stated",
    "The learning outcomes were effectively addressed in the course": "Outcomes Addressed",
    "There were constructive interactions between the instructor and the students": "Interactions",
    "The instructor was accessible for discussions about the course": "Accessible",
    "I received feedback that improved my learning in this course": "Feedback",
    "The course challenged me to do my best work": "Challenged",
    "My experience in the course increased my interest in the subject matter": "Interest",
}


def parse_course_info(filename):
    """Extract semester, year, and course from filename."""
    # Pattern: Coleman Jared <Semester> <Year> ... <Course> <Section>
    match = re.search(r"(Spring|Fall|Summer)\s+(\d{4}).*?(CMSI\s+\d+)\s+(\d+)", filename)
    if match:
        semester = match.group(1)
        year = match.group(2)
        course = match.group(3).replace(" ", " ")
        section = match.group(4)
        return f"{semester} {year}", course, section
    return "Unknown", "Unknown", "00"


def load_eval_file(filepath):
    """Load and parse a single evaluation CSV file."""
    responses = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            responses.append(row)
    return responses


def extract_ratings(responses):
    """Extract numerical ratings from responses."""
    ratings = defaultdict(list)
    effectiveness_ratings = []

    for resp in responses:
        for col, value in resp.items():
            # Likert scale questions
            for q_text, label in QUESTION_LABELS.items():
                if q_text in col and "_Comments" not in col and value in LIKERT_MAP:
                    ratings[label].append(LIKERT_MAP[value])

            # Overall effectiveness
            if "overall effectiveness" in col.lower() and "_Comments" not in col:
                if value in EFFECTIVENESS_MAP:
                    effectiveness_ratings.append(EFFECTIVENESS_MAP[value])

    return ratings, effectiveness_ratings


def extract_comments(responses):
    """Extract open-ended comments from responses."""
    beneficial_comments = []
    improvement_comments = []

    for resp in responses:
        for col, value in resp.items():
            if "most beneficial" in col.lower() and value and value != "D/A":
                beneficial_comments.append(value.strip())
            elif "more effective" in col.lower() and value and value != "D/A":
                improvement_comments.append(value.strip())

    return beneficial_comments, improvement_comments


def calculate_stats(values):
    """Calculate mean and standard deviation."""
    if not values:
        return None, None
    mean = statistics.mean(values)
    stdev = statistics.stdev(values) if len(values) > 1 else 0.0
    return mean, stdev


def filter_good_feedback(comments, min_length=50):
    """Filter for substantive positive feedback."""
    good_comments = []
    positive_keywords = [
        "great", "excellent", "helpful", "enjoyed", "liked", "appreciated",
        "well", "organized", "clear", "kind", "willing", "best", "really",
        "engaging", "informative", "thorough", "fair", "supportive"
    ]

    for comment in comments:
        if len(comment) >= min_length:
            # Check if comment is generally positive
            lower_comment = comment.lower()
            positive_count = sum(1 for kw in positive_keywords if kw in lower_comment)
            if positive_count >= 2:
                good_comments.append(comment)

    return good_comments


def main():
    evals_dir = Path(__file__).parent

    # Find 2025 evaluation files
    eval_files = list(evals_dir.glob("*2025*.csv"))

    if not eval_files:
        print("No 2025 evaluation files found.")
        return

    print("=" * 80)
    print("COURSE EVALUATION ANALYSIS - 2025")
    print("=" * 80)

    all_ratings = defaultdict(list)
    all_effectiveness = []
    all_beneficial = []
    all_improvement = []
    course_summaries = []

    for filepath in sorted(eval_files):
        semester, course, section = parse_course_info(filepath.name)
        print(f"\n{'─' * 80}")
        print(f"Course: {course} Section {section} ({semester})")
        print(f"{'─' * 80}")

        responses = load_eval_file(filepath)
        n_responses = len(responses)
        print(f"Responses: {n_responses}")

        ratings, effectiveness = extract_ratings(responses)
        beneficial, improvement = extract_comments(responses)

        # Course-level stats
        if effectiveness:
            eff_mean, eff_std = calculate_stats(effectiveness)
            print(f"\nOverall Effectiveness: {eff_mean:.2f}/5.0 (SD: {eff_std:.2f})")
            all_effectiveness.extend(effectiveness)

        print("\nQuestion Ratings:")
        for label in QUESTION_LABELS.values():
            if label in ratings and ratings[label]:
                mean, std = calculate_stats(ratings[label])
                print(f"  {label}: {mean:.2f}/5.0 (SD: {std:.2f}, n={len(ratings[label])})")
                all_ratings[label].extend(ratings[label])

        # Store for summary
        course_summaries.append({
            "semester": semester,
            "course": course,
            "section": section,
            "n_responses": n_responses,
            "effectiveness": effectiveness,
            "ratings": dict(ratings),
            "beneficial": beneficial,
            "improvement": improvement
        })

        all_beneficial.extend(beneficial)
        all_improvement.extend(improvement)

    # Aggregate statistics
    print("\n" + "=" * 80)
    print("AGGREGATE STATISTICS (All 2025 Courses)")
    print("=" * 80)

    if all_effectiveness:
        eff_mean, eff_std = calculate_stats(all_effectiveness)
        print(f"\nOverall Effectiveness: {eff_mean:.2f}/5.0 (SD: {eff_std:.2f}, n={len(all_effectiveness)})")

    print("\nAggregate Question Ratings:")
    sorted_ratings = []
    for label in QUESTION_LABELS.values():
        if label in all_ratings and all_ratings[label]:
            mean, std = calculate_stats(all_ratings[label])
            sorted_ratings.append((mean, std, label, len(all_ratings[label])))

    # Sort by mean rating (descending)
    sorted_ratings.sort(reverse=True)
    for mean, std, label, n in sorted_ratings:
        print(f"  {label}: {mean:.2f}/5.0 (SD: {std:.2f}, n={n})")

    # Top 3 highest rated
    print("\n" + "─" * 40)
    print("TOP 3 HIGHEST RATED AREAS:")
    for i, (mean, std, label, n) in enumerate(sorted_ratings[:3], 1):
        print(f"  {i}. {label}: {mean:.2f}/5.0 (SD: {std:.2f})")

    # Bottom 3 (areas for growth)
    print("\n" + "─" * 40)
    print("AREAS FOR POTENTIAL GROWTH:")
    for mean, std, label, n in sorted_ratings[-3:]:
        print(f"  • {label}: {mean:.2f}/5.0 (SD: {std:.2f})")

    # Good feedback examples
    print("\n" + "=" * 80)
    print("SELECTED POSITIVE FEEDBACK EXAMPLES")
    print("=" * 80)

    good_feedback = filter_good_feedback(all_beneficial)
    for i, comment in enumerate(good_feedback[:10], 1):
        # Truncate very long comments
        if len(comment) > 500:
            comment = comment[:500] + "..."
        print(f"\n{i}. \"{comment}\"")

    # Common themes in improvement suggestions
    print("\n" + "=" * 80)
    print("IMPROVEMENT SUGGESTIONS (Sample)")
    print("=" * 80)

    for i, comment in enumerate(all_improvement[:5], 1):
        if comment and len(comment) > 10:
            if len(comment) > 300:
                comment = comment[:300] + "..."
            print(f"\n{i}. \"{comment}\"")

    # LaTeX-ready output for FSR
    print("\n" + "=" * 80)
    print("LATEX-READY OUTPUT FOR FSR")
    print("=" * 80)

    print("\n% Highest-rated areas (aggregate):")
    print("\\begin{itemize}[leftmargin=*, nosep]")
    for mean, std, label, n in sorted_ratings[:3]:
        # Map back to full question text
        full_text = [k for k, v in QUESTION_LABELS.items() if v == label][0]
        print(f"\\item {full_text}: {mean:.2f}/5.0 (SD: {std:.2f})")
    print("\\end{itemize}")

    print("\n% Selected student feedback:")
    print("\\begin{itemize}[leftmargin=*, nosep]")
    for comment in good_feedback[:3]:
        # Clean up for LaTeX
        clean = comment.replace("&", "\\&").replace("%", "\\%").replace("$", "\\$")
        clean = clean.replace("#", "\\#").replace("_", "\\_")
        if len(clean) > 200:
            clean = clean[:200] + "..."
        print(f"\\item ``{clean}''")
    print("\\end{itemize}")


if __name__ == "__main__":
    main()
