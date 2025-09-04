import pandas as pd

# Paths to your raw files
phishing_files = [
    "data/ALL-phishing-domains.lst",
    "data/ALL-phishing-links.lst",
    "data/csv.txt"
]

benign_files = [
    "data/top-1m.csv",
    "data/tranco_VQQ6N.csv"
]

# -----------------------
# Load phishing datasets
# -----------------------
phishing_urls = []
for file in phishing_files:
    with open(file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            url = line.strip()
            if url and not url.startswith("#"):  # remove comments
                phishing_urls.append(url)

phishing_df = pd.DataFrame(phishing_urls, columns=["url"])
phishing_df["label"] = 1  # malicious = 1

# -----------------------
# Load benign datasets
# -----------------------
benign_urls = []
for file in benign_files:
    df = pd.read_csv(file, header=None)  # usually format: rank,domain
    if df.shape[1] == 2:
        domains = df[1]  # second column has domain
    else:
        domains = df[0]
    benign_urls.extend("http://" + d for d in domains)

benign_df = pd.DataFrame(benign_urls, columns=["url"])
benign_df["label"] = 0  # benign = 0

# -----------------------
# Merge and Save
# -----------------------
final_df = pd.concat([phishing_df, benign_df], ignore_index=True)

# Remove duplicates
final_df = final_df.drop_duplicates(subset=["url"]).reset_index(drop=True)

# Save processed dataset
final_df.to_csv("data/urls.csv", index=False)

print(f"✅ Final dataset saved: {len(final_df)} rows")
