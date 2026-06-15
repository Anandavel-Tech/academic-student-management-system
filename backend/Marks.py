import matplotlib.pyplot as plt

# Helper function to safely get integer input within a range
def get_int_in_range(prompt, min_val, max_val):
    while True:
        try:
            val = int(input(prompt))
            if min_val <= val <= max_val:
                return val
            else:
                print(f"Please enter a value between {min_val} and {max_val}.")
        except ValueError:
            print("Invalid input. Please enter an integer.")

# Function to compute contribution out of 15 from raw marks out of 50
def compute_ca_contributions(raw_marks):
    return (raw_marks / 50) * 15

# Ask for number of subjects
try:
    n = int(input("Enter number of subjects: "))
    if n <= 0:
        raise ValueError
except ValueError:
    print("Invalid number of subjects. Please enter a positive integer.")
    exit()

# Initialize lists
subjects = []
ca1_marks = []
ca2_marks = []
ca1_contribs = []
ca2_contribs = []
ca3_reqs = []

# Input and computation loop
for i in range(1, n + 1):
    print(f"\nSubject {i}:")
    subj_name = input("Enter subject name (optional, press Enter to skip): ").strip() or f"Subject {i}"
    ca1_raw = get_int_in_range(f"  CA1 marks out of 50 for {subj_name}: ", 0, 50)
    ca2_raw = get_int_in_range(f"  CA2 marks out of 50 for {subj_name}: ", 0, 50)

    ca1 = compute_ca_contributions(ca1_raw)
    ca2 = compute_ca_contributions(ca2_raw)
    ca3_needed = 25 - (ca1 + ca2)
    ca3_clipped = max(0, min(15, ca3_needed))

    subjects.append(subj_name)
    ca1_marks.append(ca1_raw)
    ca2_marks.append(ca2_raw)
    ca1_contribs.append(ca1)
    ca2_contribs.append(ca2)
    ca3_reqs.append(ca3_clipped)

# Display numeric results per subject
print("\nPer-subject results:")
for idx, name in enumerate(subjects):
    print(f"{idx + 1}. {name} - CA1: {ca1_marks[idx]}/50, CA2: {ca2_marks[idx]}/50, "
          f"CA1_contrib: {ca1_contribs[idx]:.2f}, CA2_contrib: {ca2_contribs[idx]:.2f}, "
          f"CA3_required (clipped): {ca3_reqs[idx]:.2f}")

# Plot grouped bar chart
x = range(n)
width = 0.25
fig, ax = plt.subplots(figsize=(10, 6))

bars1 = ax.bar([xi - width for xi in x], ca1_contribs, width, label="CA1 contrib", color="steelblue")
bars2 = ax.bar(x, ca2_contribs, width, label="CA2 contrib", color="orange")
bars3 = ax.bar([xi + width for xi in x], ca3_reqs, width, label="CA3 required (clipped)", color="green")

ax.set_xlabel("Subject")
ax.set_ylabel("Contrib / Requirement (out of 15)")
ax.set_title("CA1 and CA2 contributions and CA3 requirement per subject")
ax.set_xticks(list(x))
ax.set_xticklabels(subjects, rotation=45, ha="right")
ax.set_ylim(0, 15)
ax.legend()

# Annotate values on bars
def annotate(bars):
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontsize=8)

annotate(bars1)
annotate(bars2)
annotate(bars3)

plt.tight_layout()
plt.show()