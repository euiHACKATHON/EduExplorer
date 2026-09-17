# Mars Colony Explorer — Phaser.js Implementation Plan
**Target Framework:** Phaser 3 (HTML5 / JavaScript ES6 or TypeScript)  
**IDE/Environment:** Replit / VS Code  
**Backend Reference:** FastAPI REST Service  
**Primary Integration Method:** Code-First AI Generation (OpenAI Codex)

---

## Executive Summary & Architecture Overview

This document provides a comprehensive, code-first implementation blueprint for **Mars Colony Explorer**, a 2D educational adventure game built with **Phaser 3**. 

Unlike Unity, which relies heavily on visual editor hierarchies and binary scene assets, this Phaser 3 setup is expressed entirely in plain-text code files (`.js` / `.ts`). This makes it optimal for rapid generation, refactoring, and feature expansion using **OpenAI Codex** inside environments like **Replit**.

### Core Architectural Principles
* **Code-First Architecture:** Scene graphs, physics bodies, UI cards, and event handlers are constructed programmatically without binary scene assets.
* **API-Driven Content:** Dialogue, educational questions, hint scaffolding, and subject mastery are served dynamically via JSON over HTTP REST.
* **Dual-Mode Networking:** A built-in toggle in `APIService` allows switching between local mock JSON assets (offline development) and a live FastAPI backend.
* **Web-Native Deployment:** Runs directly in any modern browser without heavy engine builds or installation prerequisites.

```
+-----------------------------------------------------------------------------------+
|                                PHASER 3 CLIENT                                    |
|                                                                                   |
|   +---------------------+   +---------------------+   +-----------------------+   |
|   |   BootScene.js      |   |   MainMenuScene.js  |   |   MarsColonyScene.js  |   |
|   +---------------------+   +---------------------+   +-----------------------+   |
|                                                                ^                  |
|                                                                v                  |
|                             +-------------------------------------+               |
|                             |        APIService Module            |               |
|                             | (Fetch API / Mock Asset Fallback)   |               |
|                             +-------------------------------------+               |
+-----------------------------------------------------------------------------------+
                                         |
                            HTTP / REST (JSON API Payloads)
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                                FASTAPI BACKEND                                    |
|  (LLM Dynamic Dialogue / Item Response Theory / Student Mastery Database)          |
+-----------------------------------------------------------------------------------+
```

---

## 1. Project Directory Structure

```text
mars-colony-phaser/
├── index.html
├── package.json
├── vite.config.js
├── src/
│   ├── main.js
│   ├── config.js
│   ├── api/
│   │   └── APIService.js
│   ├── scenes/
│   │   ├── BootScene.js
│   │   ├── MainMenuScene.js
│   │   ├── CharacterSelectScene.js
│   │   └── MarsColonyScene.js
│   ├── entities/
│   │   ├── Player.js
│   │   └── NPC.js
│   ├── ui/
│   │   ├── DialogueUI.js
│   │   ├── ChallengeUI.js
│   │   └── ProgressUI.js
│   └── state/
│       └── GameState.js
└── public/
    ├── assets/
    │   ├── sprites/
    │   └── tilesets/
    └── mock/
        ├── dialogue_scientist_01.json
        ├── dialogue_engineer_01.json
        ├── challenge_M001.json
        ├── assessment_response.json
        ├── hint_response.json
        └── student_progress.json
```

---

## 2. Data Models & API Contracts

### Data Contracts (`APIService.js`)

#### Dialogue Request / Response
```json
// GET /ai/dialogue?npc_id=scientist_01
{
  "npc_id": "scientist_01",
  "npc_name": "Dr. Sara",
  "message": "The rover Beta is stuck in Sector 4. We need to compute required thrust using F = ma.",
  "options": [
    { "text": "I'll inspect the rover.", "action": "START_CHALLENGE", "payload": "M001" },
    { "text": "Explain Newton's Second Law again.", "action": "EXPLAIN", "payload": "FORCE_MA" }
  ]
}
```

#### Assessment Request / Response
```json
// POST /assessment
{
  "student_id": "STD_88321",
  "mission_id": "M001",
  "question_id": "Q001",
  "answer": "C",
  "time_taken": 18,
  "hints_used": 0
}

// Response
{
  "correct": true,
  "xp_earned": 100,
  "mastery": 0.78,
  "feedback": "Correct! Force = mass * acceleration (500 kg * 4 m/s² = 2000 N)."
}
```

---

## 3. Core C#/JS Code Blueprints

### A. Centralized API Manager (`src/api/APIService.js`)

```javascript
export class APIService {
  constructor(baseUrl = 'http://localhost:8000', useMock = true) {
    this.baseUrl = baseUrl;
    this.useMock = useMock;
  }

  async getNPCDialogue(npcId) {
    if (this.useMock) {
      const res = await fetch(`/public/mock/dialogue_${npcId}.json`);
      return await res.json();
    }
    const res = await fetch(`${this.baseUrl}/ai/dialogue?npc_id=${npcId}`);
    return await res.json();
  }

  async submitAssessment(payload) {
    if (this.useMock) {
      const res = await fetch('/public/mock/assessment_response.json');
      return await res.json();
    }
    const res = await fetch(`${this.baseUrl}/assessment`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return await res.json();
  }

  async requestHint(payload) {
    if (this.useMock) {
      const res = await fetch('/public/mock/hint_response.json');
      return await res.json();
    }
    const res = await fetch(`${this.baseUrl}/ai/hint`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return await res.json();
  }
}
```

---

### B. 2D Player Controller (`src/entities/Player.js`)

```javascript
import Phaser from 'phaser';

export class Player extends Phaser.Physics.Arcade.Sprite {
  constructor(scene, x, y, texture) {
    super(scene, x, y, texture);
    scene.add.existing(this);
    scene.physics.add.existing(this);
    
    this.setCollideWorldBounds(true);
    this.speed = 160;
    this.cursors = scene.input.keyboard.createCursorKeys();
    this.wasd = scene.input.keyboard.addKeys('W,A,S,D');
  }

  update() {
    this.body.setVelocity(0);

    // Horizontal movement
    if (this.cursors.left.isDown || this.wasd.A.isDown) {
      this.body.setVelocityX(-this.speed);
    } else if (this.cursors.right.isDown || this.wasd.D.isDown) {
      this.body.setVelocityX(this.speed);
    }

    // Vertical movement
    if (this.cursors.up.isDown || this.wasd.W.isDown) {
      this.body.setVelocityY(-this.speed);
    } else if (this.cursors.down.isDown || this.wasd.S.isDown) {
      this.body.setVelocityY(this.speed);
    }

    this.body.velocity.normalize().scale(this.speed);
  }
}
```

---

### C. Main Gameplay Scene (`src/scenes/MarsColonyScene.js`)

```javascript
import Phaser from 'phaser';
import { Player } from '../entities/Player';
import { APIService } from '../api/APIService';

export class MarsColonyScene extends Phaser.Scene {
  constructor() {
    super({ key: 'MarsColonyScene' });
    this.api = new APIService('http://localhost:8000', true);
  }

  create() {
    // 1. Create Tilemap or Ground Background
    this.add.grid(400, 300, 800, 600, 32, 32, 0x1f2430, 1, 0x2b3245, 1);

    // 2. Spawn Player
    this.player = new Player(this, 400, 300, 'player_sprite');

    // 3. Spawn NPC
    this.npc = this.physics.add.staticSprite(500, 200, 'npc_sara');
    this.npc.npcId = 'scientist_01';

    // 4. Interaction Prompt
    this.promptText = this.add.text(0, 0, 'Press E to interact', {
      font: '14px monospace',
      fill: '#00E5FF',
      backgroundColor: '#10141D',
      padding: { x: 6, y: 4 }
    }).setVisible(false);

    // 5. Interaction Key
    this.keyE = this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.E);
  }

  update() {
    this.player.update();

    // Check distance between player and NPC
    const dist = Phaser.Math.Distance.BetweenPoints(this.player, this.npc);
    if (dist < 50) {
      this.promptText.setPosition(this.npc.x - 50, this.npc.y - 40).setVisible(true);
      if (Phaser.Input.Keyboard.JustDown(this.keyE)) {
        this.triggerNPCDialogue(this.npc.npcId);
      }
    } else {
      this.promptText.setVisible(false);
    }
  }

  async triggerNPCDialogue(npcId) {
    const dialogueData = await this.api.getNPCDialogue(npcId);
    console.log('Dialogue received:', dialogueData);
    // Launch HTML/DOM Dialogue Overlay
    this.scene.launch('DialogueUIScene', dialogueData);
  }
}
```

---

## 4. Step-by-Step Codex Prompting Sequence

To build this project step-by-step in Replit using OpenAI Codex, submit these prompts sequentially:

1. **Step 1 — Project Initialization:**
   > *"Generate a Phaser 3 project structure using Vite. Include an index.html file, package.json, main.js game config, and four scene files: BootScene.js, MainMenuScene.js, CharacterSelectScene.js, and MarsColonyScene.js."*

2. **Step 2 — 2D Movement & Interaction:**
   > *"Write an Arcade Physics Player class in Phaser 3 supporting WASD/Arrow key movement with velocity normalization. In MarsColonyScene, add an NPC sprite and display a 'Press E to interact' floating label when the player is within 50px."*

3. **Step 3 — Network & API Layer:**
   > *"Create an APIService class using ES6 async/await fetch. Include a toggleable mock mode (`useMock = true`) that loads JSON files from `/public/mock/` for `/ai/dialogue`, `/assessment`, and `/ai/hint` endpoints."*

4. **Step 4 — UI Overlay Subsystem:**
   > *"Create a Phaser 3 UI overlay scene using HTML DOM elements or Phaser GameObjects to render dialogue boxes, choice buttons, challenge cards, and assessment feedback panels dynamically."*

---

## 5. Validation & Definition of Done Checklist

* [ ] Player moves smoothly in 2D using WASD or Arrow keys.
* [ ] Approaching an NPC displays the "Press E to interact" prompt.
* [ ] Pressing `E` loads dialogue JSON dynamically via `APIService`.
* [ ] Selecting a mission opens a 2D challenge card with dynamic multiple-choice buttons.
* [ ] Submitting an answer fires a `POST /assessment` payload and renders the feedback modal.
* [ ] Clicking "Get Hint" queries `/ai/hint` and updates the hint box.
* [ ] Setting `useMock = false` connects to the FastAPI backend without requiring code changes to gameplay scenes.
