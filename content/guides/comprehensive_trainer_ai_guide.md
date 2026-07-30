# Comprehensive Trainer AI Guide

This guide provides a detailed explanation of the advanced Trainer AI system in Pokemon Xhenos. The AI employs sophisticated decision-making algorithms that simulate realistic trainer behavior through multi-layered analysis, probability-based choices, switch-in simulation, and continuous expected-value scoring rather than fixed heuristic buckets.

---

## 1. Core AI Philosophy & Architecture

### Decision Framework
The AI operates on a **dual-evaluation system**:
- **Pokemon Scoring** (`scorePokemon`): Each Pokemon (including the current one) receives a numerical score based on matchup analysis
- **Move Scoring** (`scoreMove`): Each available move is scored based on damage potential, utility, and strategic value

### Primary Objectives (in priority order)
1. **Maximize Survival**: Avoid unnecessary knockouts through smart switching
2. **Optimize Damage Output**: Prioritize moves that deal significant damage or secure KOs
3. **Strategic Utility**: Use status moves, hazards, and effects when they provide measurable advantages
4. **Maintain Unpredictability**: Use weighted randomization to avoid being exploited

### Design Principle: Continuous Formulas Over Fixed Buckets
Earlier versions of this AI evaluated Pokemon matchups using discrete "buckets" — fixed point penalties for "enemy can KO me," fixed bonuses for "I can KO the enemy," evaluated somewhat independently of each other. This produced two categories of bad decisions:

- **Double-counting**: A Pokemon that would die to the foe could get penalized twice (once for a flat "will die" penalty, once again for a separate "foe can KO" penalty), while a Pokemon that resists the foe's *current* move but is actually doomed by a different move in the foe's kit wasn't penalized enough.
- **Cliff effects**: A Pokemon dealing 99% max damage and one dealing 105% max damage were both simply "kills," even though the first one is not guaranteed to actually secure the KO once damage roll variance is considered.

The current system (see **Section 2.4**) replaces these buckets with a single continuous expected-value formula driven by kill *probability* rather than kill *booleans*, so nearby situations produce nearby scores and utility moves (like hazard removal) aren't unfairly crushed just because the user happens to be slower.

---

## 2. Switching Decision Algorithm

### When Switching is Considered
The AI evaluates switching in several scenarios:

- **Forced Switch**: When all valid moves have 0 PP (100% switch chance if possible)
- **Free Switch**: When the current Pokemon faints, or after a pivot move — no move is being chosen, just the next Pokemon
- **Matchup Disadvantage**: When teammates would perform significantly better than the current Pokemon (mid-turn switching, difficulty > Normal only)
- **KO Avoidance**: When the opponent can KO but a teammate would survive better

### 2.1 Switch-In Simulation

Before the AI scores any potential switch-in, it accounts for what will actually happen *the moment that Pokemon enters the field* — entry hazards (Stealth Rock, Spikes, etc.), weather/ability triggers (Intimidate, Drought, Sand Stream, etc.), and any other on-switch-in effects. This is handled by `simulateSwitchIn`, which:

1. Takes a **clone** of the candidate Pokemon (never the real one — this is a hypothetical)
2. Calls `swapIn(foe, true, field)` on the clone with hazards enabled, so all on-entry effects actually resolve
3. Records the HP lost and any stat stage changes for debug logging
4. Returns the modified clone, now reflecting realistic post-switch-in HP and stats

This means a Pokemon weak to Stealth Rock isn't scored as if it's still at full HP — its score reflects the HP it will realistically have the instant it's on the field.

### 2.2 Unified Switch-In Evaluation

**Both** switch-in code paths — the mid-turn "should I switch instead of attacking" decision in `bestMove2`, and the free-switch decision (fainted Pokemon / after a pivot move) — now go through the same evaluation pipeline: `evaluateSwitchInScore`. This was previously a source of bugs, since the free-switch path skipped hazard/ability simulation entirely and the forced-switch path was recalculating the foe's threat using stale data left over from whichever Pokemon was active before.

```java
// Convenience overload - clones everything itself. Used for free switches.
public int evaluateSwitchInScore(Pokemon foe, Field field)

// Core version - caller supplies pre-made clones to avoid redundant cloning
// in hot loops (bestMove2 already clones the whole team up front).
public int evaluateSwitchInScore(Pokemon myClone, Pokemon foe, Pokemon foeClone, Field fieldClone)
```

The core method:
1. Runs `simulateSwitchIn` on the candidate to get accurate post-entry HP/stats
2. Recalculates the foe's **actual best move against this specific candidate** (not whatever was strongest against the Pokemon that just left) — this matters a lot for type-resistant switch-ins, since the foe's most threatening move against the old active Pokemon is often completely different from their most threatening move against the new one
3. Feeds that fresh threat data into `scorePokemon` for a final score

Because both switch paths call the same method, any future improvement to switch-in evaluation (new held item interactions, better speed-tier handling, etc.) only needs to be written once and both paths benefit immediately.

### 2.3 Pokemon Scoring System (`scorePokemon`)

Each Pokemon receives a comprehensive score based on:

#### Matchup Evaluation (see Section 2.4)
- Continuous expected-value score based on kill probability in both directions and turn order

#### Offensive Potential
- **Best Attack Score**: Highest-scoring offensive move available (from `scoreMove`)
- **Best Status Score**: Highest-scoring utility move available (from `scoreMove`)

#### Status Penalties
- **Toxic Damage**: -10 points per toxic counter
- **Leech Seed**: -30 points
- **Yawning/Drowsy Status**: -60 points
- **Cursed**: -80 points
- **Perish Song**: Exponentially increasing penalty (up to -320 points as the counter approaches 1)

#### Special Considerations
- **Natural Cure Ability**: Penalty applied when currently statused (accounts for the fact that switching would cure it, so staying in "wastes" the status)
- **Red Card / Eject Button Items**: When the overall score is negative, a stat-boost bonus is applied to reflect the forced-switch utility these items provide against the opponent
- **Magic Bounce / Mouthwater Abilities**: Bonus against hazard-setting opponents whose hazards would bounce back onto them

### 2.4 The Matchup Expected-Value Formula

This is the core replacement for the old "enemy can KO / dies to enemy" flat penalties. Rather than treating "will this Pokemon die" and "will this Pokemon kill" as booleans evaluated in isolation, `matchupScore` computes a single continuous value driven by **turn order** (a genuine discontinuity — whoever acts first really does get to act first) and **kill probability in both directions** (a continuous value, since damage rolls have variance and a 99%-max-damage hit is not equivalent to a guaranteed kill).

```java
private static final double KILL_VALUE = 90;
private static final double DEATH_VALUE = -90;
private static final double CHIP_WEIGHT = 15;    // credit for damage dealt without a kill
private static final double THREAT_WEIGHT = 45;  // cost of remaining exposed to foe's damage
private static final double DELAY_WEIGHT = 20;   // extra cost of killing only after taking a hit
private static final double TEMPO_WEIGHT = 10;   // pure "who acts first" value when nothing dies

public static double matchupScore(int myMaxMoveScore, double foeMaxDamagePercent, boolean iAmFaster)
```

**Inputs:**
- `myMaxMoveScore` — the higher of this Pokemon's best attacking or best status move score (from `scoreMove`). A raw move score above ~100 reliably indicates a move that secures a KO, so this is used directly as a stand-in for "how close to a guaranteed kill is my best option" without recalculating damage a second time.
- `foeMaxDamagePercent` — the foe's highest max-roll damage percentage against this Pokemon, already computed while scanning the foe's moveset for other purposes (hazard-bounce checks, etc.), so this is reused rather than recalculated.
- `iAmFaster` — whether this Pokemon acts before the foe this turn.

**Behavior by turn order:**

- **If I'm faster:** the foe only gets to act with probability `(1 - atkFrac)` — i.e., only if my move doesn't secure the kill. If I do kill, the foe's damage is irrelevant, since they never act. This mirrors the "doesn't matter if the foe could have KO'd me back" case — a fast kill scores close to `KILL_VALUE` regardless of how hard the foe hits.
- **If the foe is faster:** I only get to act with probability `(1 - defFrac)` — i.e., only if the foe's hit doesn't kill me first. If the foe kills me, my own damage output becomes irrelevant (I never got to use it), and the score converges toward `DEATH_VALUE` regardless of how strong my move was. A "slow kill" (I'm outsped but still kill the foe on my turn) scores well below a fast kill, discounted by `DELAY_WEIGHT` for the damage I had to absorb to get there.
- **Stalemates** (neither side can kill): both branches collapse toward `atkFrac * CHIP_WEIGHT - defFrac * THREAT_WEIGHT`, with a small `TEMPO_WEIGHT` bonus/penalty for simply acting first or last. Critically, when `defFrac` (the threat against me) is small — e.g. a hazard-removal Pokemon that isn't seriously threatened by the current opponent — the threat penalty is nearly zero, so the matchup score stays close to neutral and doesn't drown out that Pokemon's genuine utility value (Rapid Spin, Defog, etc.) coming from `scoreMove`.

This produces (without ever hardcoding a bucket) the following approximate ordering, matching intended design intent:

**Fast kill > Slow kill > Faster stalemate ≈ 0 > Slower stalemate ≈ 0 > Dies to enemy (regardless of own kill potential, once outsped)**

Because everything is computed from two continuous fractions (`atkFrac`, `defFrac`) rather than discrete cases, small changes in damage percentages (e.g. a Life Orb boost pushing a move from 97% to 103% max roll) produce smoothly varying scores instead of a sudden jump across a bucket boundary.

### Switch Decision Process
1. **Score Comparison**: Calculate scores for current Pokemon vs. all teammates (via `evaluateSwitchInScore`, accounting for hazards/abilities on entry)
2. **Weight Calculation**: Only teammates with higher positive scores than the current Pokemon are considered
3. **Probability Determination**: Switch chance = min(95%, |score_difference| / 2)
4. **Final Decision**: Weighted random selection among viable switches, weighted by `(scoreDiff)^2 + 10`

### Pivot Move Integration
Before committing to a switch, the AI checks for **pivot moves** (U-turn, Volt Switch, etc.) via `hasPivotMove`:

- Only used if the move would actually connect (type effectiveness > 0 for attacks, utility check via `isUsefulPivot` for status pivots)
- Allows safe switching while dealing damage or applying effects
- Integrated into the switch timing logic — the AI checks for a pivot option before falling back to a "hard" switch (`Status.SWAP`)

The AI also recognizes when it has a **free switch vs. having to take a hit**. For example, if the player Pokemon has already moved (slow U-Turn) or the current Pokemon fainted, the AI just picks its best matchup directly via `evaluateSwitchInScore` rather than worrying about a pivot move it doesn't need.

---

## 3. Move Selection System (`scoreMove`)

### Move Scoring Components

#### Damage Analysis
- **Base Damage**: Raw damage calculation against opponent via `calcWithTypes`
- **HP Percentage Damage**: Damage relative to opponent's current HP
- **KO Potential**: Major bonus for moves that can secure knockout (`willKill = damagePercent >= foeHPPercent`)
- **Speed Priority**: Extra bonuses for faster KOs vs. slower KOs

#### Accuracy Considerations
- **Accuracy Modifier**: Moves are penalized based on miss chance (`getEffectiveAccuracy`)
- **Risk Assessment**: Low-accuracy moves need proportionally higher payoff; an explicit penalty is applied below 90% accuracy (skipped for Blunder Policy holders)
- **Perfect Accuracy**: Moves with ≥100% accuracy treated as guaranteed hits and given an extra bonus

#### KO-Specific Bonuses
- **Fast KO**: +50 points for outspeeding with a lethal move
- **Slow KO**: +20 points for a KO even when slower
- **Base KO Bonus**: +40 points for any KO potential
- **Priority KO**: Additional `12 + (priority_level × 3)` points
- **Special KO Moves**: Fell Stinger, Comet Punch get an additional +25 points on a kill

#### Risk Mitigation
- **Recoil Penalties**: Moves that would KO the user via recoil receive -45 points (skipped for Rock Head, Magic Guard, Scaly Skin)
- **HP Threshold Checks**: Recoil moves heavily penalized at low HP based on the specific move's recoil fraction (Head Smash: 1/2, Submission/Take Down: 1/4, others: 1/3)

### Status Move Intelligence

The AI uses a sophisticated **effect simulation system** (`isUsefulEffect`) to determine status move utility rather than hardcoding a list of "good" targets for every move:

#### Utility Testing Process
1. **Clone Environment**: Creates copies of both Pokemon and the field
2. **Simulate Move**: Applies the move's primary/secondary/status effects in the test environment (with `createTask` disabled so no real game-visible side effects occur)
3. **Compare States**: Analyzes what changed between before/after states across stat stages, status, volatile statuses, HP, item, field effects, ability, typing, disabled moves, perish count, weather/terrain, and forced-switch state
4. **Multi-Target Testing**: For moves that don't "do anything" against the active Pokemon, the AI selects one random opposing team member (if they can switch) to test the move against instead. The resulting score is scaled down accordingly — a move only useful against a benched Pokemon is valued lower than one useful against the current target.

**Example:**
```
Houndoom with Will-O-Wisp against an already-burned Pokemon
- The AI sees that Will-O-Wisp doesn't affect the statused Pokemon (nothing changed in the test environment)
- It then checks one of the player's party Pokemon to test against instead
- If it picks someone that can be burned, Will-O-Wisp's use chance is roughly half of normal
- If the player's Pokemon can't switch, or the back Pokemon also can't be burned, the move scores as not useful
```

#### Utility Detection Criteria
A status move is considered useful if it causes at least one of the following in the simulation:

- **Stat Stage Changes**: Opponent's stats decrease or user's stats increase
- **Status Conditions**: Opponent gains negative status, user cures status
- **Field Effects**: Hazards set (or cleared, for Rapid Spin/Defog), screens broken (Brick Break/Psychic Fangs), weather/terrain changed
- **Item Changes**: Beneficial item swapping (Trick, Switcheroo)
- **HP Changes**: User heals (excluding self-damaging moves like Belly Drum/Curse/Healing Wish/Lunar Dance/Memento)
- **Type/Ability Changes**: Meaningful alterations to the opponent
- **Move Restrictions**: Disable, Torment, Taunt effects applying
- **Forced Switches**: Detected via a change in the foe trainer's `current` reference

### Specialized Move Heuristics

#### Hazard Moves (Stealth Rock, Spikes, etc.)
- **Team Analysis**: Evaluates opponent's entire team for hazard vulnerability via `isHazardUseful` and a per-team-member scan in `scoreMove`
- **Immunity Checks**: Accounts for Heavy-Duty Boots, Magic Guard, Scaly Skin, Shield Dust, grounding, and Poison-type immunity to Toxic Spikes
- **Layer Limits**: Won't stack hazards beyond their maximum layers (Spikes: 3, Toxic Spikes: 2)
- **Damage Calculation**: Stealth Rock's per-target value scales with type effectiveness against that specific team member

#### Disruption Moves
- **Disable/Torment/Hex Claw**: Higher value against Pokemon with limited movesets — big bonus if it's their only valid move, moderate bonus if it's their only damaging move
- **Encore/Spotlight Ray**: Penalized if the foe only has one valid move anyway (nothing to lock them into)
- **Taunt**: Checks ratio of status vs. attacking moves in the opponent's set — rewarded when the opponent has real status options to shut down, penalized otherwise

#### Defensive Moves
- **Endure**: Bonus when the opponent can KO (+20 points)
- **Destiny Bond**: Bonus when the opponent can KO (+50), penalized otherwise (-20)
- **Counter/Mirror Coat/Metal Burst**: Scales with expected incoming damage, only considered when the move wouldn't already be redundant with a guaranteed kill and the foe can't already KO first (unless Focus Band is held)

#### Field Control
- **Rapid Spin/Defog/Field Flip**: Value scales with the number of hazard layers currently present on the user's side
- **Phasing Moves** (Dragon Tail, Circle Throw, Whirlwind, Roar): Bonus scales with the opponent's current stat boosts via `calcStatBoostScore`
- **Healing Wish/Lunar Dance**: Value scales with the most-benefited teammate's missing HP and status

### Emergency Situations
When the opponent can KO this turn, the AI prioritizes:

- **Priority Moves**: Large bonus for a move that can act first to secure one last hit, provided the AI is otherwise slower than the foe
- **Last-Resort Options**: Destiny Bond and Endure become highly valued specifically in this state

---

## 4. Aggression Scaling (Difficulty > Normal)

For difficulties above Normal, the AI computes an **aggression factor** via `calculateDefensiveResponse` before scoring any moves. This is separate from the matchup EV formula above — it doesn't change *whether* a Pokemon is a good switch-in, it changes *how much the AI leans into its strongest attacking option* once it's decided who's staying in.

### Algorithm
1. Find the AI's strongest damaging move against the current foe
2. Calculate the survival ratio if the current Pokemon stays in (`1 - maxDamagePercent/100`)
3. Simulate switching each back-line Pokemon in (via `simulateSwitchIn`, to account for hazards) and calculate their survival ratio against the AI's strongest move
4. Take the maximum of "stay in" vs. "best possible switch" survival — this represents the opponent's best defensive response
5. Convert survival into aggression via `aggression = 1.2 + 1.8 * (1 - bestDefensiveResponse)^2`, clamped to `[1.0, 3.0]`

Intuitively: if the opponent has no good defensive answer to the AI's best attack (low `bestDefensiveResponse`), the AI becomes more aggressive, since there's little downside to attacking hard right now.

### Applying Aggression (`applyAggression`)
Rather than directly scaling scores (which could explode for high-scoring moves), aggression is applied via **normalized exponentiation**:
1. Find the maximum move score
2. Normalize all positive scores to `[0, 1]` by dividing by the max
3. Raise each normalized score to the aggression power
4. Scale back up by the original max

This sharpens the probability distribution toward the AI's best move(s) as aggression increases, without changing the *relative ranking* of moves or producing runaway values. Non-positive scores are left untouched — aggression never props up a move the AI has already determined is a bad idea.

---

## 5. Advanced Decision-Making Features

### Probability-Based Selection
Rather than always choosing the highest-scored option, the AI uses **weighted randomization**:

- Moves with positive scores get probability weights based on their (aggression-scaled) scores
- Higher-scoring moves are more likely but not guaranteed
- Prevents predictable play patterns while maintaining strategic soundness

### Fallback Systems
1. **Positive Move Selection**: Choose from moves with positive scores, weighted by score
2. **Least-Bad Selection**: If all moves score non-positively, pick the highest-scoring one anyway
3. **Random Selection**: Final fallback if scoring produces no usable result at all

### Context Awareness
- **Difficulty Scaling**: Normal difficulty uses simpler heuristic thresholds for switching (perish count, all-moves-do-nothing checks); higher difficulties use the full scored switch-evaluation pipeline plus aggression scaling
- **Team Composition**: Considers teammates' capabilities directly via `evaluateSwitchInScore` on the full team
- **Field State**: Accounts for weather, terrain, and existing field effects throughout scoring
- **Item Integration**: Factors in held items for both sides (Heavy-Duty Boots, Focus Band, Eject Button, Red Card, Blunder Policy, Covert Cloak, Power Herb, etc.)

### Anti-Exploitation Measures
- **Randomization Layers**: Multiple independent sources of controlled randomness (move selection, switch selection, secondary effect proc chance in `isUsefulEffect`'s back-check)
- **Score Variance**: Prevents purely deterministic play at the same matchup
- **Adaptive Thresholds**: Switch probability and move probability both scale continuously with score differences rather than using hard cutoffs

---

## 6. Technical Implementation Details

### Performance Optimizations
- **Shared Team Cloning**: `bestMove2` clones the entire trainer team and the opposing team once at the start of the method, rather than re-cloning per candidate
- **Reused Damage Calculations**: The matchup formula reuses `foeMaxDamageP` and the best move score already computed elsewhere in `scorePokemon`, rather than recalculating foe damage a second time
- **Unified Switch-In Pipeline**: `evaluateSwitchInScore` is shared between the forced-switch and free-switch code paths (see Section 2.2), so simulation logic only needs to be implemented and maintained once
- **Early Termination**: The foe's damage scan breaks early once a guaranteed KO move is found, skipping evaluation of the rest of their moveset

### Debug Systems
The AI provides comprehensive logging to console/terminal:

- **Pokemon Scores**: All team member evaluations with breakdowns, including the new `[MATCHUP]` line showing the inputs and output of the expected-value formula:
  ```
  [MATCHUP] Icy Serpent: myMoveScore=68 foeDmg=100% outsped => -19.4
  ```
- **Move Scores**: Individual move ratings and reasoning
- **Switch Probabilities**: Calculated chances for each potential switch, plus the underlying score differences driving them
- **Switch-In Effects**: HP lost and stat changes from entry hazards/abilities during simulation
- **Aggression Calculation**: Full breakdown of the survival-ratio-to-aggression formula per turn, including which back Pokemon produced the best defensive response
- **Decision Reasoning**: String explanations for chosen actions (e.g. `[Perish in 1 : 100%]`, `[Score diff switch : 42.5%]`)

### Error Handling
- **Graceful Degradation**: System continues functioning even with missing data (e.g. no valid attacking moves falls back to a default moderate aggression factor)
- **Validation Checks**: Ensures moves and switches are legal before execution
- **Boundary Conditions**: Handles edge cases like struggle-only situations and 0-PP movesets

### Testing Strategy
Because the matchup formula is now a pure function of three inputs (`myMaxMoveScore`, `foeMaxDamagePercent`, `iAmFaster`), it can be unit tested directly without constructing full `Pokemon`/`Trainer`/`Field` objects — useful properties to assert include:
- A faster Pokemon never scores worse than an otherwise-identical slower one at the same damage values
- Increasing the AI's own damage output never decreases its score
- A guaranteed fast kill scores near the formula's maximum regardless of the foe's damage output
- A guaranteed death while outsped scores near the formula's minimum regardless of the AI's own damage output
- A low-threat stalemate (both sides doing minimal damage) stays close to zero rather than being crushed by the threat term

In-game validation is still valuable alongside unit tests, since hazard interactions, ability-based speed/damage changes on switch-in, and other systemic effects can only really be verified by watching real `[MATCHUP]` and switch-in debug output during actual battles — a dedicated gauntlet-team setup (several Pokemon deliberately built to land in different matchup regions against a specific lead) is a good way to exercise this systematically.

---

## 7. Strategic Implications

### Player Interaction
The AI creates engaging gameplay through:

- **Intelligent Pressure**: Makes optimal plays when given opportunities
- **Realistic Mistakes**: Occasional suboptimal choices maintain believability
- **Adaptive Challenge**: Responds meaningfully to player strategies, including recognizing when a favorable-looking switch-in is actually a trap (e.g. a Pokemon that resists the current threat but loses to a second move in the foe's kit is no longer scored as safe)

### Competitive Viability
- **Meta Understanding**: Recognizes and responds to common strategies
- **Resource Management**: Conserves powerful moves and healthy Pokemon
- **Win Condition Focus**: Prioritizes paths to victory over individual exchanges

### Learning Opportunities
Players can improve by:

- **Battle Betting**: The Casino Battle Bet minigame displays the % chance the AI had of making a given decision (switching/move selection)
    - *Example: `Roserade used Sludge Bomb! [42.5% chance]`*
    - *Example: `Trainer A withdrew Houndoom! [55.3% chance]`*
- **Observing AI Decisions**: Understanding optimal play patterns
- **Exploiting Randomness**: Finding edges in the AI's probability-based choices, or "outs" as they're often called
    - *Example: If the AI thinks I'm going to switch it might use a suboptimal move, so I can risk staying in here!*
- **Strategic Adaptation**: Countering the AI's preferred strategies

---

## 8. Real Battle Examples

***These examples use actual console output from the AI system during live battles, showing real decision-making in action. Exact score values reflect the specific scoring version they were captured on — the underlying reasoning shown is representative of current behavior.***

#### Player Pokemon:
```
Glimmora @ Hard Stone
Ability: Toxic Debris
- Power Gem
- Energy Ball
- Mortal Spin
- Toxic
```

#### AI Team:

```
Gyarados @ Sitrus Berry  
Ability: Intimidate  
- Bounce  
- Waterfall  
- Crunch  
- Ice Fang  

Conkeldurr @ Life Orb  
Ability: Iron Fist  
- Mach Punch  
- Hammer Arm  
- Knock Off  
- Fire Punch  

Ludicolo @ Leftovers  
Ability: Swift Swim  
- Energy Ball  
- Hydro Pump  
- Rain Dance  
- Ice Beam
```

### Scenario 1: Switching Decision

**Current Matchup:** Gyarados vs. Glimmora (both at full HP)

**AI's Threat Assessment:**

- Glimmora threatens ~70-90% damage with Power Gem (Rock-type super effective vs. Flying)
- Gyarados's Waterfall deals only ~30-40% damage due to Poison resisting Water in this game

```
AI sees that Glimmora is threatening a strong Power Gem
AI evaluates each teammate as a switch-in via evaluateSwitchInScore
(each candidate is simulated with entry hazards/abilities applied first)

[MATCHUP] Gyarados: myMoveScore=38 foeDmg=82% outsped => -71.4
[MATCHUP] Conkeldurr: myMoveScore=142 foeDmg=8% faster => +88.1
[MATCHUP] Ludicolo: myMoveScore=51 foeDmg=64% outsped => -19.2

Evaluation:
- Gyarados vs Glimmora: -83 (takes a lot from Power Gem, doesn't do much back with Waterfall)
- Conkeldurr vs Glimmora: +102 (type advantage, can OHKO with Hammer Arm, resists Rock)
- Ludicolo vs Glimmora: +3 (takes more from Power Gem and doesn't do much back)

Result: 92.5% chance to switch to Conkeldurr
```

### Scenario 2: Move Selection

**Same Matchup:** Gyarados vs. Glimmora (Gyarados outspeeds)

```
Available Moves:
- Ice Fang:  +27 points (small boost for Frostbite chance and Flinch chance)
- Crunch:    +33 points (slightly bigger boost for 30% Defense drop chance)
- Bounce:    +25 points (does the least damage but gets a boost for useful Paralysis chance)
- Waterfall: +44 points (most damage and gets a boost for Flinch chance)

Probabilities: Ice Fang 20.9%, Crunch 25.6%, Bounce 19.4%, Waterfall 34.1%

The damages of the moves are all pretty similar
(since Poison resists Water in this game, 3/4 attacks are neutral),
so the resulting scores — and therefore probabilities — are pretty similar too.
```

### Scenario 3: Fast-Kill vs. Slow-Kill Discrimination

**Illustrative Matchup:** A fast Poison/Ice attacker (player) vs. a bulky Ground-type trainer Pokemon that resists the player's Poison-type move but is outsped and OHKO'd by the player's Ice-type move.

```
[MATCHUP] Ground-type: myMoveScore=140 foeDmg=100% outsped => -71.8

The candidate resists the foe's current move (low damage from Poison alone),
but the matchup formula correctly identifies that the foe's *Ice* move outspeeds
and kills regardless of the Ground-type's own kill potential — because once the
foe is faster and lands a KO, the candidate's own damage output never comes into
play. This produces a strongly negative score despite the type resistance,
correctly discouraging the switch.
```

---

## 9. Limitations and Design Philosophy

### Intentional Limitations
- **Realistic Evaluation**: Makes decisions based on observable information (the AI doesn't "know" the player's exact click in advance, only threat likelihoods)
- **Human-Like Errors**: Probability system allows for suboptimal choices occasionally

### Balance Considerations
- **Challenge Level**: Provides difficulty without being unfair (such as knowing what move you'll click)
- **Player Agency**: Maintains opportunities for skillful play and counterplay
- **Engagement**: Creates interesting decision points for both AI and player

### Future Extensibility
The system is designed to accommodate:

- **New Moves**: Additional moves can be integrated into existing scoring via `scoreMove`'s move-specific heuristic block
- **Ability Expansion**: New abilities can modify existing calculations, particularly within `simulateSwitchIn` and `isUsefulEffect`
- **Meta Evolution**: Heuristics and the matchup formula's weight constants (`KILL_VALUE`, `DEATH_VALUE`, `CHIP_WEIGHT`, `THREAT_WEIGHT`, `DELAY_WEIGHT`, `TEMPO_WEIGHT`) can be retuned as a group for different competitive environments or difficulty tiers without restructuring the underlying formula
- **Difficulty-Scaled Matchup Weights**: The aggression system (Section 4) already demonstrates a pattern for difficulty-dependent behavior; the matchup formula's weights are a natural extension point for the same kind of scaling

---

This AI system represents a sophisticated approach to Pokemon battle simulation, balancing competitive-level decision-making with engaging, human-like gameplay patterns. The multi-layered scoring system, unified switch-in simulation, continuous expected-value matchup formula, probability-based selection, and comprehensive utility evaluation create an opponent that feels both challenging and fair.