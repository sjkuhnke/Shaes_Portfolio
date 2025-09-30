# Comprehensive Trainer AI Guide

This guide provides a detailed explanation of the advanced Trainer AI system in Pokemon Xhenos. The AI employs sophisticated decision-making algorithms that simulate realistic trainer behavior through multi-layered analysis, probability-based choices, and complex heuristics.

---

## 1. Core AI Philosophy & Architecture

### Decision Framework
The AI operates on a **dual-evaluation system**:
- **Pokemon Scoring**: Each Pokemon (including the current one) receives a numerical score based on matchup analysis
- **Move Scoring**: Each available move is scored based on damage potential, utility, and strategic value

### Primary Objectives (in priority order)
1. **Maximize Survival**: Avoid unnecessary knockouts through smart switching
2. **Optimize Damage Output**: Prioritize moves that deal significant damage or secure KOs
3. **Strategic Utility**: Use status moves, hazards, and effects when they provide measurable advantage
4. **Maintain Unpredictability**: Use weighted randomiza-tion to avoid being exploited

---

## 2. Switching Decision Algorithm

### When Switching is Considered
The AI evaluates switching in several scenarios:

- **Forced Switch**: When all valid moves have 0 PP (100% switch chance if possible)
- **Matchup Disadvantage**: When teammates would perform significantly better
- **KO Avoidance**: When the opponent can KO but a teammate would survive better

### Pokemon Scoring System
Each Pokemon receives a comprehensive score based on:

#### Defensive Metrics
- **Damage Intake**: How much damage the opponent's strongest move would deal
- **Type Matchup**: Factors in type/ability interactions with move types to mirror what would happen in battle
- **Speed Comparison**: Whether the Pokemon outspeeds the opponent

#### Offensive Potential
- **Best Attack Score**: Highest-scoring offensive move available
- **Best Status Score**: Highest-scoring utility move available
- **KO Potential**: Whether any move can secure a knockout
- **Fast vs. Slow Kill**: Fast Kills are heavily incentivized

#### Status Penalties
- **Toxic Damage**: -10 points per toxic counter
- **Leech Seed**: -30 points
- **Yawning Status**: -60 points
- **Cursed**: -80 points
- **Perish Song**: Exponentially increasing penalty (up to -320 points)

#### Special Considerations
- **Regenerator Ability**: Bonus for switching out (scales with missing HP)
- **Natural Cure Ability**: Bonus when statused (-50 points)
- **Red Card Item**: Stat boost bonus when losing
- **Magic Bounce Ability**: Bonus against hazard-setting opponents

### Switch Decision Process
1. **Score Comparison**: Calculate scores for current Pokemon vs. all teammates
2. **Weight Calculation**: Only teammates with higher positive scores are considered
3. **Probability Determination**: Switch chance = min(95%, |score_difference| / 2)
4. **Final Decision**: Weighted random selection among viable switches

### Pivot Move Integration
Before committing to a switch, the AI checks for **pivot moves** (U-turn, Volt Switch, etc.):

- Only used if the move would actually connect (type effectiveness > 0 for attacks, utility check for status pivots)
- Allows safe switching while dealing damage or applying effects
- Integrated into the switch timing logic

The AI also recognizes when they have a **free switch vs. having to take a hit**. For example, if the player Pokemon has already moved (slow U-Turn), the AI will just go into their best matchup against you instead of worrying about having to switch in on your move.

---

## 3. Move Selection System

### Move Scoring Components

#### Damage Analysis
- **Base Damage**: Raw damage calculation against opponent
- **HP Percentage Damage**: Damage relative to opponent's current HP
- **KO Potential**: Major bonus for moves that can secure knockout
- **Speed Priority**: Extra bonuses for faster KOs vs. slower KOs

#### Accuracy Considerations
- **Accuracy Modifier**: Moves are penalized based on miss chance
- **Risk Assessment**: Low-accuracy moves need proportionally higher payoff
- **Perfect Accuracy**: Moves with >100% accuracy treated as guaranteed hits

#### KO-Specific Bonuses
- **Fast KO**: +50 points for outspeeding with lethal move
- **Slow KO**: +20 points for KO even when slower
- **Base KO Bonus**: +40 points for any KO potential
- **Priority KO**: Additional +12 + (priority_level × 3) points
- **Special KO Moves**: Fell Stinger, Comet Punch get +20 points

#### Risk Mitigation
- **Recoil Penalties**: Moves that would KO the user receive -45 points
- **Self-Damage Consideration**: Accounts for abilities like Rock Head, Magic Guard
- **HP Threshold Checks**: Recoil moves heavily penalized at low HP

### Status Move Intelligence

The AI uses a sophisticated **effect simulation system** to determine status move utility:

#### Utility Testing Process
1. **Clone Environment**: Creates copies of both Pokemon, trainers, and field
2. **Simulate Move**: Applies the move's effects in the test environment
3. **Compare States**: Analyzes what changed between before/after states
4. **Multi-Target Testing**: For moves that don't "do anything" against the active Pokemon, it will then select a random opposing team member (if they can switch) to see if the move would effect them instead. The score is adjusted accordingly (less likely if the active Pokemon wouldn't be affected but a team member would be).

**Example:**
```
Houndoom with Will-O-Wisp against an already burned Pokemon
- The AI will see that Will-O-Wisp doesn't effect the statused Pokemon (nothing changed in the test environment)
- It will then check one of the player's party Pokemon to test against.
- If it picks someone that can be burned, then the chance to use Will-O-Wisp will be half as likely as normal.
- If the player's Pokemon can't switch or the back Pokemon also can't be burned, then it won't be able to use Will-O-Wisp
```


#### Utility Detection Criteria
A status move is considered useful if it causes at least one of the following:

- **Stat Stage Changes**: Opponent's stats decrease or user's stats increase
- **Status Conditions**: Opponent gains negative status, user cures status
- **Field Effects**: Hazards set, screens broken, weather/terrain changed
- **Item Changes**: Beneficial item swapping (Trick, Switcheroo)
- **HP Changes**: User heals (excluding self-damaging moves)
- **Type/Ability Changes**: Meaningful alterations to opponent
- **Move Restrictions**: Disable, Torment, Taunt effects apply

### Specialized Move Heuristics

#### Hazard Moves (Stealth Rock, Spikes, etc.)
- **Team Analysis**: Evaluates opponent's entire team for hazard vulnerability
- **Immunity Checks**: Accounts for Heavy-Duty Boots, Magic Guard, Flying types
- **Layer Limits**: Won't stack hazards beyond their maximum layers
- **Damage Calculation**: Stealth Rock uses type effectiveness multipliers

#### Disruption Moves
- **Disable/Torment**: Higher value against Pokemon with limited movesets
- **Encore**: Evaluated based on opponent's last move and available options
- **Taunt**: Checks ratio of status vs. attacking moves in opponent's set

#### Defensive Moves
- **Endure**: Bonus when opponent can KO (+20 points)
- **Destiny Bond**: Situational bonus (+25 points)
- **Counter/Mirror Coat/Metal Burst**: Scales with expected incoming damage as long as it doesn't KO

#### Field Control
- **Rapid Spin/Defog**: Value based on number of hazard layers present
- **Phasing Moves**: Bonus scales with opponent's stat boosts
- **Weather/Terrain**: Evaluated for team synergy benefits

### Emergency Situations
When the opponent can KO, the AI prioritizes:

- **Priority Moves**: Massive bonus for moves that can act first to get one last hit off
- **Last Resort Options**: Destiny Bond, Endure become highly valued

---

## 4. Advanced Decision-Making Features

### Probability-Based Selection
Rather than always choosing the highest-scored option, the AI uses **weighted randomization**:

- Moves with positive scores get probability weights based on their scores
- Higher-scoring moves are more likely but not guaranteed
- Prevents predictable play patterns while maintaining strategic soundness

### Fallback Systems
1. **Positive Move Selection**: Choose from moves with positive scores
2. **Least-Bad Selection**: If all moves score negatively, pick the highest score
3. **Random Selection**: Final fallback if scoring system fails

### Context Awareness
- **Turn-Based Adjustments**: Different priorities based on battle progression
- **Team Composition**: Considers teammates' capabilities in decision-making
- **Field State**: Accounts for weather, terrain, and field effects
- **Item Integration**: Factors in held items for both sides

### Anti-Exploitation Measures
- **Randomization Layers**: Multiple sources of controlled randomness
- **Score Variance**: Prevents purely deterministic play
- **Adaptive Thresholds**: Decision boundaries adjust based on game state

---

## 5. Technical Implementation Details

### Performance Optimizations
- **Shallow Cloning**: Efficient copying for simulation testing
- **Cached Calculations**: Damage calculations reused where possible
- **Early Termination**: Skip unnecessary evaluations when outcomes are clear

### Debug Systems
The AI currently provides comprehensive logging in a console/terminal:

- **Pokemon Scores**: All team member evaluations with breakdowns
- **Move Scores**: Individual move ratings and reasoning
- **Switch Probabilities**: Calculated chances for each potential switch
- **Decision Reasoning**: String explanations for chosen actions

### Error Handling
- **Graceful Degradation**: System continues functioning even with missing data
- **Validation Checks**: Ensures moves and switches are legal before execution
- **Boundary Conditions**: Handles edge cases like struggle-only situations

---

## 6. Strategic Implications

### Player Interaction
The AI creates engaging gameplay through:

- **Intelligent Pressure**: Makes optimal plays when given opportunities
- **Realistic Mistakes**: Occasional suboptimal choices maintain believability
- **Adaptive Challenge**: Responds meaningfully to player strategies

### Competitive Viability
- **Meta Understanding**: Recognizes and responds to common strategies
- **Resource Management**: Conserves powerful moves and healthy Pokemon
- **Win Condition Focus**: Prioritizes paths to victory over individual exchanges

### Learning Opportunities
Players can improve by:

- **Battle Betting**: The Casino Battle Bet minigame will display the % chance that the AI had to make that decision (switching/move selection)
    - *Example: `Roserade used Sludge Bomb! [42.5% chance]`*
    - *Example: `Trainer A withdrew Houndoom! [55.3% chance]`*
- **Observing AI Decisions**: Understanding optimal play patterns
- **Exploiting Randomness**: Finding edges in AI's probability-based choices, or "outs" as they're often called
    - *Example: If the AI thinks I'm going to switch it might use a suboptimal move, so I can risk staying in here!*
- **Strategic Adaptation**: Countering AI's preferred strategies

---

## 7. Real Battle Examples

***These examples use actual console output from the AI system during live battles, showing real decision-making in action.***

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
AI Sees that Glimmora is threatening a strong Power Gem
AI will then check to see if it should switch someone into Power Gem

Evaluation:
- Gyarados vs Glimmora: -83 (Takes a lot from Power Gem, doesn't do too much back with Waterfall)
- Conkeldurr vs Glimmora: +102 (type advantage, can OHKO with Hammer Arm, resists Rock)
- Ludicolo vs Glimmora: +3 (takes more from Power Gem and doesn't do much back)

Result: 92.5% chance to switch to Conkeldurr
```

### Scenario 2: Move Selection

**Same Matchup:** Gyarados vs. Glimmora (Gyarados outspeeds)

```
Available Moves:
- Ice Fang:  +27 points (gets a tiny boost for the Frostbite chance and the Flinch chance)
- Crunch:    +33 points (gets a slightly bigger boost for 30% Defense drop chance)
- Bounce:    +25 points (does the least damage but gets a boost for useful Paralysis chance)
- Waterfall: +44 points (most damage and gets a boost for Flinch chance)

Probabilities: Ice Fang 20.9%, Crunch 25.6%, Bounce 19.4%, Waterfall 34.1%

The damages of the moves are all pretty similar:
- (since Poison resists Water in this game, 3/4 attacks are neutral)
So therefore the scores are pretty similar too.
```

---

## 8. Limitations and Design Philosophy

### Intentional Limitations
- **Realistic Evaluation**: Makes decisions based on observable information
- **Human-Like Errors**: Probability system allows for suboptimal choices occasionally

### Balance Considerations
- **Challenge Level**: Provides difficulty without being unfair (such as knowing what move you'll click)
- **Player Agency**: Maintains opportunities for skillful play and counterplay
- **Engagement**: Creates interesting decision points for both AI and player

### Future Extensibility
The system is designed to accommodate:

- **New Moves**: Additional moves can be integrated into existing scoring
- **Ability Expansion**: New abilities can modify existing calculations
- **Meta Evolution**: Heuristics can be adjusted for different competitive environments

---

This AI system represents a sophisticated approach to Pokemon battle simulation, balancing competitive-level decision-making with engaging, human-like gameplay patterns. The multi-layered scoring system, probability-based selection, and comprehensive utility evaluation create an opponent that feels both challenging and fair.