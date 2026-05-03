from mc_intervene.worlds.policy_world import generate_policy_worlds
from mc_intervene.renderers.policy_renderers import render_policy_world
from mc_intervene.operators.policy_uncertainty import apply_all_policy_uncertainty_operators
from mc_intervene.interventions.policy_interventions import build_policy_intervention_spec
from mc_intervene.interventions.validation import validate_policy_intervention_spec


def main():
    world = generate_policy_worlds(n_worlds=1, seed=67)[0]
    view = render_policy_world(world, "policy_excerpt")
    uncertain_views = apply_all_policy_uncertainty_operators(world, view)

    print("=" * 100)
    print("HIDDEN WORLD")
    print("=" * 100)
    print(world)
    print("GROUND TRUTH:", world.ground_truth)
    print("EXPLANATION:", world.decision_explanation())

    for uv in uncertain_views:
        spec = build_policy_intervention_spec(world, uv)
        validate_policy_intervention_spec(uv, spec)

        print("\n" + "=" * 100)
        print("OPERATOR:", uv.uncertainty_operator)
        print("UNCERTAINTY SOURCE:", uv.uncertainty_source)
        print("RECOVERABILITY:", uv.recoverability_type)
        print("-" * 100)
        print("PROMPT:")
        print(uv.prompt_text)
        print("-" * 100)
        print("HINT EFFECT:", spec.hint_effect)
        print("HINT VALUE:", spec.intervention_value_hint)
        print("HINT PAYLOAD:", spec.hint_payload)
        print("-" * 100)
        print("VERIFY EFFECT:", spec.verify_effect)
        print("VERIFY VALUE:", spec.intervention_value_verify)
        print("VERIFY PAYLOAD:", spec.verification_payload)
        print("-" * 100)
        print("OPTIMAL FIRST:", spec.optimal_first_action)
        print("OPTIMAL FINAL:", spec.optimal_final_action)
        print("ACCEPTABLE FIRST:", spec.acceptable_first_actions)
        print("NOTES:", spec.policy_notes)


if __name__ == "__main__":
    main()
