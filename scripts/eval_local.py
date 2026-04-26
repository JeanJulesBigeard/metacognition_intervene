import argparse
import pandas as pd

from mc_intervene.eval_local import evaluate_dataframe, summarize_results
from mc_intervene.local_model import OllamaPolicy
from mc_intervene.scoring import score_mc_intervene_v6_episode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--provider", default="ollama")
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    df = pd.read_csv(args.data)
    if args.limit:
        df = df.head(args.limit).copy()

    if args.provider == "ollama":
        policy = OllamaPolicy(model=args.model, base_url=args.base_url)
    else:
        raise ValueError(f"Unsupported provider: {args.provider}")

    results = evaluate_dataframe(df, policy, score_mc_intervene_v6_episode)
    print(summarize_results(results))
    print("\nBy subtype:")
    print(results.groupby("subtype")["final_score"].mean())


if __name__ == "__main__":
    main()