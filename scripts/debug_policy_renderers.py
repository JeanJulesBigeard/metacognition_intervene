from mc_intervene.worlds.policy_world import generate_policy_worlds
from mc_intervene.renderers.policy_renderers import render_all_policy_views


def main():
    world = generate_policy_worlds(n_worlds=1, seed=67)[0]

    print("=" * 80)
    print("HIDDEN WORLD")
    print("=" * 80)
    print(world)
    print("Ground truth:", world.ground_truth)
    print("Explanation:", world.decision_explanation())

    for view in render_all_policy_views(world):
        print("\n" + "=" * 80)
        print("VIEW:", view.view_type)
        print("=" * 80)
        print(view.prompt_text)
        print("\nStructured metadata:")
        print("contains_threshold:", view.contains_threshold)
        print("contains_exception:", view.contains_exception)
        print("contains_form_requirement:", view.contains_form_requirement)
        print("visible_facts:", view.visible_facts)
        print("visible_policy_parts:", view.visible_policy_parts)


if __name__ == "__main__":
    main()
