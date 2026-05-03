from mc_intervene.worlds.policy_world import generate_policy_worlds
from mc_intervene.renderers.policy_renderers import render_policy_world
from mc_intervene.operators.policy_uncertainty import apply_all_policy_uncertainty_operators
from mc_intervene.operators.validation import validate_uncertain_policy_view


def main():
    world = generate_policy_worlds(n_worlds=1, seed=67)[0]
    view = render_policy_world(world, "policy_excerpt")

    print("=" * 100)
    print("HIDDEN WORLD")
    print("=" * 100)
    print(world)
    print("Ground truth:", world.ground_truth)
    print("Explanation:", world.decision_explanation())

    uncertain_views = apply_all_policy_uncertainty_operators(world, view)

    for uv in uncertain_views:
        validate_uncertain_policy_view(uv)
        print("\n" + "=" * 100)
        print("OPERATOR:", uv.uncertainty_operator)
        print("SOURCE:", uv.uncertainty_source)
        print("RECOVERABILITY:", uv.recoverability_type)
        print("SUGGESTED FIRST:", uv.suggested_optimal_first_action)
        print("SUGGESTED FINAL:", uv.suggested_optimal_final_action)
        print("HIDDEN FIELDS:", uv.hidden_fields)
        print("DEGRADED FIELDS:", uv.degraded_fields)
        print("-" * 100)
        print(uv.prompt_text)


if __name__ == "__main__":
    main()
