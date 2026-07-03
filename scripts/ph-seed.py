"""
ph-seed — Seed a PH project directory from a test fixture.

Reads a fixture YAML and writes a pre-populated manifest.yaml so that
when you run /rhdp-publishing-house, it skips intake and goes straight
to the approval gate.

Usage:
    python scripts/ph-seed.py onboarded/ansible --project-dir /tmp/ph-test
    python scripts/ph-seed.py onboarded/ansible  # uses current dir

After seeding:
    claude --plugin-dir ~/work/code/rhdp-publishing-house/skills-plugin
    /rhdp-publishing-house
    # → reads manifest, sees intake done, goes to approval gate
"""

import sys
import os
import argparse
import yaml
import subprocess
from pathlib import Path
from datetime import date

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

FIXTURES_DIR = PROJECT_ROOT / "test" / "fixtures"
TEMPLATE_REPO = "https://github.com/rhpds/rhdp-publishing-house-template.git"

PRODUCT_TYPE_MAP = {
    "ansible": "workshop",
    "ai": "workshop",
    "openshift": "workshop",
    "rhel": "workshop",
    "demo": "demo",
}

MODE_MAP = {
    "onboarded": "rhdp_published",
    "self-published": "self_published",
    "express": "express",
}

def load_env_from_creds() -> None:
    creds_file = Path.home() / ".rhdp-creds.md"
    if not creds_file.exists():
        return
    for line in creds_file.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, _, value = line.strip().partition("=")
            if key.strip() in ("MAAS_API_BASE", "MAAS_API_KEY"):
                if not os.environ.get(key.strip()):
                    os.environ[key.strip()] = value.strip()

def generate_with_llm(prompt: str, system: str = "") -> str:
    """Call LiteMaaS Haiku to generate content."""
    import openai
    api_key = os.environ.get("MAAS_API_KEY")
    if not api_key:
        return ""  # Fall back silently if no key
    client = openai.OpenAI(
        api_key=api_key,
        base_url=os.environ.get("MAAS_API_BASE", "https://maas-rhdp.apps.maas.redhatworkshops.io/v1"),
    )
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        resp = client.chat.completions.create(
            model=os.environ.get("MAAS_TESTER_MODEL", "claude-haiku-4-5"),
            max_tokens=2048,
            messages=messages,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        print(f"⚠️  LLM generation failed: {e} — using stub", file=sys.stderr)
        return ""


def generate_design_md(fixture: dict, project_name: str) -> str:
    """Generate a realistic design.md from fixture data using LiteMaaS Haiku."""
    prompt = f"""Write a Publishing House design spec for this lab project.

Project: {project_name}
Initial Prompt: {fixture.get('initial_prompt', '')}
Follow-up Details: {fixture.get('follow_up_details', '')}

Write EXACTLY this structure (no preamble, start with #):

# {project_name}

## Problem Statement
[2-3 sentences describing the problem this lab solves]

## Target Audience
- **Role:** [who attends]
- **Experience level:** [beginner/intermediate/advanced]
- **What they already know:** [prerequisites]
- **Prerequisites:** [what to have ready]

## Learning Objectives
1. [first objective]
2. [second objective]
3. [third objective]

## Content Type
Workshop (hands-on)

## Products & Technologies
- [product 1]
- [product 2]

## Infrastructure Requirements
[What the environment needs: cluster type, resources, special workloads]

## Modules
[List 2-4 modules with title and 1-sentence description each]
"""
    result = generate_with_llm(prompt)
    if result:
        return result

    # Fallback stub
    return f"""# {project_name}

## Problem Statement
{fixture.get('initial_prompt', 'TBD')[:300]}

## Target Audience
- **Role:** TBD
- **Experience level:** Intermediate
- **Prerequisites:** None

## Learning Objectives
1. TBD
2. TBD
3. TBD

## Content Type
Workshop (hands-on)

## Products & Technologies
- {fixture.get('product', 'OpenShift').title()}

## Infrastructure Requirements
TBD — populated during intake
"""


def generate_module_outline(fixture: dict, module_num: int, module_title: str, duration: str = "30 min") -> str:
    """Generate a module outline using LiteMaaS Haiku."""
    prompt = f"""Write a Publishing House module outline for module {module_num}.

Project context: {fixture.get('initial_prompt', '')[:300]}
Follow-up details: {fixture.get('follow_up_details', '')[:300]}
Module title: {module_title}

Write EXACTLY this structure:

# Module {module_num}: {module_title}

## Brief Overview
[2-3 sentences describing this module]

## Audience and Time
- **Target personas:** [who this is for]
- **Prerequisites:** [what you need]
- **Estimated duration:** {duration}

## What You Will See, Learn, and Do

**See:**
- [what learners observe]

**Learn:**
- [key concepts]

**Do:**
- [hands-on steps]

## Environment
[What's pre-provisioned for this module]
"""
    result = generate_with_llm(prompt)
    if result:
        return result
    return f"# Module {module_num}: {module_title}\n\nTBD — generated during intake\n"


def seed_manifest(fixture_path: Path, project_dir: Path) -> None:
    """Write a pre-populated manifest.yaml from fixture data."""
    with open(fixture_path) as f:
        fixture = yaml.safe_load(f)

    mode = fixture.get("mode", "onboarded")
    product = fixture.get("product", "openshift")
    name = fixture.get("name", f"{product}-workshop")
    today = date.today().isoformat()

    manifest = {
        "project": {
            "name": name.replace("-", " ").title(),
            "id": name,
            "created": today,
            "owner_name": "Test User",
            "owner_github": "test-user",
            "type": PRODUCT_TYPE_MAP.get(product, "workshop"),
            "deployment_mode": MODE_MAP.get(mode, "rhdp_published"),
            "autonomy": "supervised",
        },
        "lifecycle": {
            "current_phase": "approval",
            "phases": {
                "intake": {
                    "status": "completed",
                    "completed_at": today,
                    "assignees": ["test-user"],
                    "artifacts": ["publishing-house/spec/design.md"],
                    "summary": fixture.get("initial_prompt", "")[:200].strip(),
                },
                "vetting": {
                    "status": "completed",
                    "completed_at": today,
                    "assignees": [],
                    "result": "approved",
                    "rcars_response": "No overlapping content found.",
                },
                "spec_refinement": {
                    "status": "completed",
                    "completed_at": today,
                    "assignees": [],
                    "artifacts": ["publishing-house/spec/design.md"],
                },
                "approval": {
                    "status": "pending",
                    "approved_by": None,
                    "completed_at": None,
                },
                "writing": {
                    "status": "pending",
                    "assignees": [],
                    "modules": [],
                },
                "automation": {
                    "status": "pending",
                    "assignees": [],
                },
                "editing": {
                    "status": "pending",
                    "assignees": [],
                },
                "code_security_review": {
                    "status": "pending",
                    "assignees": [],
                },
                "final_review": {
                    "status": "pending",
                    "assignees": [],
                },
                "ready_for_publishing": {
                    "status": "pending",
                    "completed_at": None,
                },
            },
        },
    }

    ph_dir = project_dir / "publishing-house"
    ph_dir.mkdir(parents=True, exist_ok=True)
    spec_dir = ph_dir / "spec"
    spec_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = ph_dir / "manifest.yaml"
    with open(manifest_path, "w") as f:
        f.write("# RHDP Publishing House — Project Manifest (seeded by ph-seed)\n")
        f.write(f"# Fixture: {fixture_path.name}\n")
        f.write(f"# Seeded: {today}\n\n")
        yaml.dump(manifest, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # Generate realistic design.md using Haiku
    print("  Generating design.md via LiteMaaS Haiku...")
    project_name = manifest["project"]["name"]
    design_content = generate_design_md(fixture, project_name)
    design_path = spec_dir / "design.md"
    design_path.write_text(design_content)

    # Generate module outlines
    modules_dir = spec_dir / "modules"
    modules_dir.mkdir(exist_ok=True)
    # Extract module count from follow_up_details (default 3)
    follow_up = fixture.get("follow_up_details", "")
    import re
    m = re.search(r"(\d+)\s+module", follow_up, re.IGNORECASE)
    num_modules = int(m.group(1)) if m else 3
    num_modules = min(num_modules, 5)  # cap at 5

    module_slugs = []
    print(f"  Generating {num_modules} module outlines...")
    for i in range(1, num_modules + 1):
        module_title = f"Module {i}"
        outline = generate_module_outline(fixture, i, module_title)
        # Extract real title from LLM output if generated
        first_line = outline.strip().split("\n")[0]
        if first_line.startswith("# Module"):
            module_title = first_line.replace(f"# Module {i}:", "").strip()
        slug = f"module-{i:02d}-{module_title.lower().replace(' ', '-')[:30]}"
        module_slugs.append(slug)
        (modules_dir / f"{slug}.md").write_text(outline)

    # Update manifest with module list
    manifest["lifecycle"]["phases"]["intake"]["artifacts"] += [
        f"publishing-house/spec/modules/{s}.md" for s in module_slugs
    ]
    manifest["lifecycle"]["phases"]["writing"]["modules"] = [
        {"id": s, "title": s.replace("-", " ").title(), "status": "pending"} for s in module_slugs
    ]

    # Rewrite manifest with modules
    with open(manifest_path, "w") as f:
        f.write("# RHDP Publishing House — Project Manifest (seeded by ph-seed)\n")
        f.write(f"# Fixture: {fixture_path.name}\n")
        f.write(f"# Seeded: {today}\n\n")
        yaml.dump(manifest, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # Generate automation-manifest.yaml using Haiku
    print("  Generating automation-manifest.yaml...")
    auto_manifest_prompt = f"""Generate an automation manifest YAML for this lab project.

Project: {manifest["project"]["name"]}
Mode: {fixture.get("mode", "onboarded")}
Product: {fixture.get("product", "openshift")}
Follow-up Details: {fixture.get("follow_up_details", "")[:400]}

Write a valid YAML automation manifest with these fields filled in (no comments, no placeholders):

approach: ansible

infrastructure:
  type: <ocp-cnv or ocp-aws or sandbox-tenant — choose based on product>
  ocp_version: "<version>"
  multi_user: <true/false>
  users_per_deployment: <number>

operators:
  - name: <operator name if needed>
    channel: <channel>

applications:
  - name: <app name>
    namespace: <namespace>

seed_data:
  - description: <what data to pre-load>

provision_data:
  - key: <key>
    description: <what to expose to user>

notes: "<brief note about what the environment provides>"

Only include sections that are relevant. Keep it concise."""

    auto_content = generate_with_llm(auto_manifest_prompt)
    auto_manifest_path = project_dir / "publishing-house" / "spec" / "automation-manifest.yaml"
    if auto_content and auto_content.strip():
        # Strip markdown code fences if Haiku wrapped it
        clean = auto_content.strip()
        if clean.startswith("```"):
            lines = clean.split("\n")
            clean = "\n".join(l for l in lines if not l.strip().startswith("```"))
        auto_manifest_path.write_text(f"# Automation Manifest — generated by ph-seed from fixture\n# Review before automation code is written\n\n{clean}\n")
    else:
        # Minimal fallback based on product
        product = fixture.get("product", "openshift")
        infra_type = "ocp-cnv" if product in ("ai", "openshift") else "sandbox-tenant" if product == "ansible" else "ocp-aws"
        auto_manifest_path.write_text(f"""# Automation Manifest — seeded from fixture
# Review before automation code is written

approach: ansible

infrastructure:
  type: {infra_type}
  ocp_version: "4.16"
  multi_user: true
  users_per_deployment: 1

notes: "Generated by ph-seed — review and update for actual environment requirements"
""")

    # Write minimal worklog
    worklog_path = project_dir / "publishing-house" / "worklog.yaml"
    worklog_path.write_text(f"""# Publishing House Worklog
# Session notes seeded by ph-seed — ready for approval gate.
entries:
  - id: "{today}-seed-001"
    timestamp: "{today}T09:00:00Z"
    author: "ph-seed"
    status: open
    type: note
    content: "Project seeded from fixture: {fixture_path.name}. Intake, vetting, and spec refinement pre-populated. Ready for approval gate review."
""")

    print(f"✅ Seeded project at: {project_dir}")
    print(f"   manifest.yaml → approval gate ready")
    print(f"   spec/design.md → stub created")
    print()
    print("Next:")
    print(f"  cd {project_dir}")
    print(f"  claude --plugin-dir ~/work/code/rhdp-publishing-house/skills-plugin")
    print(f"  /rhdp-publishing-house")
    print(f"  # → reads manifest, sees intake done, presents approval gate")

def clone_template(project_dir: Path) -> None:
    """Clone the template repo from GitHub into the project directory."""
    temp_clone_dir = project_dir / ".template-clone"
    try:
        # Clone repo to temp location
        subprocess.run(
            ["git", "clone", TEMPLATE_REPO, str(temp_clone_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
        
        # Copy contents (excluding .git) to project_dir
        for item in temp_clone_dir.iterdir():
            if item.name == ".git":
                continue
            dest = project_dir / item.name
            if not dest.exists():
                if item.is_dir():
                    import shutil
                    shutil.copytree(item, dest)
                else:
                    import shutil
                    shutil.copy2(item, dest)
        
        print(f"✅ Cloned template from {TEMPLATE_REPO}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to clone template: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Clean up temp clone directory
        import shutil
        if temp_clone_dir.exists():
            shutil.rmtree(temp_clone_dir)

def main():
    load_env_from_creds()

    parser = argparse.ArgumentParser(description="Seed a PH project from a fixture")
    parser.add_argument("fixture", help="Fixture path (e.g. onboarded/ansible)")
    parser.add_argument("--project-dir", help="Project directory (default: /tmp/ph-seed-<fixture>)")
    parser.add_argument("--reset", action="store_true",
                        help="Wipe publishing-house/ dir and regenerate all artifacts from scratch")
    args = parser.parse_args()

    fixture_path = FIXTURES_DIR / f"{args.fixture}.yaml"
    if not fixture_path.exists():
        print(f"❌ Fixture not found: {fixture_path}")
        sys.exit(1)

    if args.project_dir:
        project_dir = Path(args.project_dir)
    else:
        import tempfile
        project_dir = Path(tempfile.mkdtemp(prefix=f"ph-seed-{args.fixture.replace('/', '-')}-"))

    import shutil

    if args.reset and project_dir.exists():
        # Wipe entire publishing-house/ (manifest, spec, worklog) — regenerate all
        ph_dir = project_dir / "publishing-house"
        if ph_dir.exists():
            shutil.rmtree(ph_dir)
            print(f"🔄 Reset: cleared publishing-house/ in {project_dir}")
        clone_template(project_dir)
    elif not project_dir.exists() or not (project_dir / "publishing-house").exists():
        clone_template(project_dir)
    else:
        # Dir exists — always overwrite manifest.yaml and re-generate spec artifacts
        print(f"ℹ️  Dir exists — regenerating publishing-house artifacts...")
        # Wipe only spec/ and manifest (keep content/ and automation/ if user edited them)
        ph_dir = project_dir / "publishing-house"
        spec_dir = ph_dir / "spec"
        if spec_dir.exists():
            shutil.rmtree(spec_dir)
        manifest_path = ph_dir / "manifest.yaml"
        if manifest_path.exists():
            manifest_path.unlink()
        print(f"   (use --reset to also wipe content/ and automation/ for a full restart)")

    seed_manifest(fixture_path, project_dir)

if __name__ == "__main__":
    main()
