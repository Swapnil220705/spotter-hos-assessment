# Spotter Full Stack Developer Assessment - Project Instructions

## 1. Project Overview

This repository is for the Spotter AI Full Stack Developer coding assessment.

The goal is to build a full-stack application using Django and React that takes trip details as input and generates:

1. A planned truck route.
2. Route information and stops/rests displayed on a map.
3. Filled-out ELD / Driver's Daily Log sheets.
4. Multiple daily log sheets when a trip spans multiple days.

The application must be accurate, usable, visually polished, and suitable for evaluation through the hosted version.

---

## 2. Official Assessment Requirements

The assessment requires:

### Technology
- Backend: Django
- Frontend: React
- The application must have a live hosted version.
- The GitHub repository must contain the source code.
- A 3-5 minute Loom video must demonstrate the application and code.

### Inputs

The application must accept:

- Current location
- Pickup location
- Dropoff location
- Current Cycle Used (hours)

### Outputs

The application must provide:

- A map showing the route.
- Information regarding stops and rests.
- A free map API must be used.
- Filled-out daily ELD log sheets.
- Multiple log sheets for longer trips.

### Assessment Assumptions

Unless the application explicitly provides a future option to configure them, use these assessment assumptions:

- Property-carrying driver.
- 70 hours / 8 days cycle.
- No adverse driving conditions.
- Fueling at least once every 1,000 miles.
- 1 hour for pickup.
- 1 hour for dropoff.

Do not silently introduce different assumptions.

---

## 3. FMCSA Source of Truth

The provided FMCSA document:

"Interstate Truck Driver's Guide to Hours of Service for Property Carriers - April 2022"

is the primary source for HOS and Driver's Daily Log behavior required by this assessment.

Do not invent, simplify, or alter an HOS rule when the provided FMCSA document specifies the behavior.

Important rules from the provided source include:

### 14-Hour Driving Window

A driver may have a period of 14 consecutive hours in which they may drive up to 11 hours after the required off-duty period.

The 14-hour window begins when the driver starts any kind of work.

After the 14-hour period ends, the driver cannot drive again until the required qualifying off-duty period has been completed.

### 11-Hour Driving Limit

The driver may drive for no more than 11 total hours during the applicable driving window.

Driving is also restricted when the required 30-minute break has not been taken after the applicable cumulative driving period.

### 30-Minute Break

The provided FMCSA guide states that a 30-minute consecutive break from driving is required after 8 cumulative hours of driving.

The break may be:
- On duty
- Off duty
- Sleeper berth

The break must be consecutive.

### 70-Hour / 8-Day Limit

For this assessment, use the 70-hour / 8-day schedule.

The limit is based on a rolling 8-day period.

Once the driver reaches the applicable limit, additional on-duty non-driving work may still be possible, but driving is not permitted until sufficient hours become available again.

### 34-Hour Restart

The FMCSA guide allows a property-carrying driver to restart the applicable 60/70-hour calculation after at least 34 consecutive hours off duty or in the sleeper berth, or a combination of both, subject to the rule.

The assessment does not explicitly require a configurable restart feature. Do not add unnecessary complexity unless it is needed by the scheduling logic.

### Sleeper Berth

The FMCSA guide contains specific sleeper-berth provisions.

Do not implement a simplified sleeper-berth calculation if the application claims to support those provisions.

If the initial implementation does not support complex split-sleeper scenarios, clearly scope the implementation rather than pretending unsupported behavior is supported.

---

## 4. Driver's Daily Log / ELD Requirements

The generated daily log must follow the structure described by the provided FMCSA guide.

The graph contains four duty statuses:

1. Off Duty
2. Sleeper Berth
3. Driving
4. On Duty (Not Driving)

The daily log should represent the driver's duty status over a 24-hour period.

The log should include, where applicable:

- Date
- Total miles driven
- Carrier
- Main office information
- Driver information
- Vehicle information
- Co-driver information if applicable
- Total hours by duty status
- Shipping information
- Remarks
- Driver certification/signature area

The Remarks section should contain the location associated with duty-status changes as required by the source document.

The generated graph should visually resemble the supplied FMCSA Driver's Daily Log rather than merely presenting the information as a text table.

For trips spanning multiple days, generate a separate daily log for each required calendar day.

---

## 5. Scheduling Engine Principles

The HOS scheduling engine is the most important business-logic component of the application.

Do not calculate a trip simply by dividing total travel time across days.

The scheduler must create a chronological sequence of events and ensure that the resulting schedule respects the applicable HOS constraints.

A conceptual event sequence may include:

- Off duty
- Driving
- Fueling
- 30-minute break
- Required rest
- Pickup
- Dropoff
- Other on-duty non-driving activity

The exact implementation should be determined during architecture/design.

The scheduling engine should be deterministic where possible.

Given the same:
- locations
- route result
- current cycle used
- configuration

it should produce the same schedule.

---

## 6. Route Planning

Use a free map/routing API as required by the assessment.

The application should obtain enough route information to determine:

- Route geometry
- Total distance
- Estimated travel duration
- Appropriate route locations for planned stops

The route API and geocoding provider must be chosen deliberately.

Do not add a paid API dependency unless explicitly approved.

API keys and secrets must never be hardcoded into source code.

Use environment variables for secrets and configuration.

---

## 7. Fuel Stops

The assessment assumes fueling at least once every 1,000 miles.

The trip planner should therefore account for fuel stops when the planned route distance requires them.

Fuel stops should appear consistently in:

- The schedule
- The map
- The event timeline
- The appropriate ELD log as on-duty non-driving time

Do not claim that a specific fuel location is real unless the routing/place API actually provides it.

---

## 8. Pickup and Dropoff

The assessment assumes:

- Pickup = 1 hour
- Dropoff = 1 hour

These periods are work/on-duty time and must be represented appropriately in the generated schedule and ELD logs.

The pickup and dropoff locations should be visible in the route/map presentation.

---

## 9. Architecture Principles

Use a clean separation of responsibilities.

The backend should own business-critical scheduling and HOS logic.

The frontend should primarily handle:

- User input
- Presentation
- Map visualization
- Schedule visualization
- ELD log visualization
- Loading/error/empty states
- User interactions

Do not duplicate HOS calculations independently in both frontend and backend.

There should be a single authoritative scheduling implementation.

Prefer small, focused modules and functions over large monolithic files.

Avoid unnecessary abstractions and premature optimization.

---

## 10. API Design

The backend should expose a clear API between React and Django.

The exact endpoint structure should be decided during the architecture phase.

API responses should use predictable structures.

Errors should be handled explicitly.

Do not expose secrets or sensitive configuration to the frontend.

---

## 11. UI / UX Requirements

UI/UX is explicitly important in the assessment.

The application should feel like a polished real product rather than a raw coding prototype.

Prioritize:

- Clear visual hierarchy
- Clean layout
- Responsive design
- Good spacing
- Clear labels
- Useful loading states
- Useful error states
- Empty states where appropriate
- Clear route information
- Easy-to-understand HOS timeline
- Easy navigation between multiple daily logs
- Consistent styling
- Readable typography
- Accessible controls

Avoid unnecessary animations or visual effects that do not improve usability.

Functionality and clarity are more important than decorative design.

---

## 12. ELD Visualization Principles

The ELD log renderer should use the actual generated schedule/events as its source of truth.

Do not manually create separate hardcoded log data for the UI.

The process should conceptually be:

Trip input
→ Route
→ Schedule/events
→ Daily event grouping
→ ELD log rendering

This ensures that the map, schedule and ELD logs remain consistent.

A change to the schedule should automatically affect the relevant visualizations.

---

## 13. Testing Requirements

Every important feature must be tested before being considered complete.

At minimum, test:

- Short trips
- Trips requiring a rest period
- Trips requiring multiple days
- Trips requiring fuel stops
- Pickup/dropoff integration
- Different current cycle-used values
- Approaching the 70-hour limit
- 30-minute break requirements
- 14-hour window constraints
- 11-hour driving constraints
- Generation of multiple daily logs
- Correct total hours in each daily log
- Correct chronological ordering of events

Test edge cases rather than only the happy path.

Do not declare a feature complete merely because the application renders without an error.

---

## 14. Development Workflow

This project must be developed in small, controlled chunks.

Do NOT attempt to build the entire application in one step.

For each meaningful task:

1. Understand the requirement.
2. Plan the implementation.
3. Implement only that task.
4. Run relevant tests.
5. Run the application where appropriate.
6. Inspect the result.
7. Fix issues.
8. Review the implementation.
9. Only then move to the next task.

Keep changes focused.

Avoid modifying unrelated files.

If a task requires changes outside the expected scope, explain why before making broad changes.

---

## 15. Git Workflow

This project is tracked with Git from the beginning.

Create meaningful commits at stable milestones.

Do not create a commit for every tiny change.

Examples of appropriate milestones:

- Project initialization
- Backend foundation
- Routing integration
- HOS scheduler implementation
- ELD log generation
- Frontend foundation
- Map integration
- UI completion
- Testing/fixes
- Deployment preparation

Commit messages should be clear and descriptive.

Never force-push or rewrite Git history unless explicitly requested.

Never commit:
- API keys
- passwords
- tokens
- private credentials
- local environment files containing secrets
- unnecessary generated files

---

## 16. AI Agent Rules

This project is being developed with AI assistance.

The AI agent must:

- Inspect existing code before modifying it.
- Understand the current project state before starting a task.
- Make the smallest reasonable change for the requested task.
- Avoid rewriting working code unnecessarily.
- Avoid changing unrelated files.
- Explain significant architectural decisions.
- Run tests after meaningful implementation changes.
- Report test results honestly.
- Never claim that something works without actually verifying it.
- Never fabricate API behavior, library behavior, test results, or external information.

If requirements are ambiguous, do not silently guess.

State the ambiguity and request clarification or use the authoritative project source when available.

---

## 17. No Hallucination Rule

Accuracy is more important than appearing confident.

When information is not known:

- Say that it is unknown.
- Inspect the repository if the answer may already exist there.
- Check the provided assessment/source material when applicable.
- Verify external technical information when necessary.
- Do not invent requirements.
- Do not invent API responses.
- Do not invent HOS rules.
- Do not invent test results.
- Do not claim successful deployment unless deployment has actually been verified.

If an implementation intentionally simplifies a requirement, document the limitation clearly.

---

## 18. Scope Control

The assessment has a maximum target of 16 work hours over no more than 4 days.

Prioritize the required assessment functionality.

Do NOT spend significant time on features that are not required, such as:

- Authentication
- User accounts
- Admin dashboards
- Multi-tenant architecture
- Complex database features
- Advanced analytics
- Unnecessary settings
- Unnecessary animations
- Features not requested by the assessment

If time is limited, prioritize:

1. Correct trip planning
2. Correct HOS scheduling
3. Correct ELD logs
4. Correct map visualization
5. Good UI/UX
6. Reliability
7. Deployment
8. Documentation and presentation

---

## 19. Current Project State

At the beginning of implementation:

- Git repository has been initialized.
- GitHub remote is configured.
- `main` branch exists.
- Initial repository commit has been made.
- Working tree is clean.
- Project folder is:
  `C:\Users\swapn\projects\spotter-hos-assessment`
- No application implementation has started yet.

Before beginning a new task, inspect the current repository state rather than assuming the project is still at the initial state.

---

## 20. Important Instruction

Do not start implementing the complete application merely because this file contains the full requirements.

The project must first go through:

1. Requirements analysis
2. Architecture/design
3. HOS scheduling design
4. Technology/API decisions
5. Implementation in small chunks

The human developer will review important plans and milestones before implementation proceeds.

When asked to work on a task, focus only on the requested task unless a dependency makes another change necessary.

Always preserve working functionality while extending the application.