import fs from "node:fs";
const missions = [
  {
    mission_id: "M001",
    question_id: "Q001",
    title: "Unstick the rover",
    subject: "Physics",
    context:
      "Rover Beta is stuck in Sector 4. Help Dr. Sara calculate the net force needed to get it moving.",
    question:
      "A 500 kg rover needs an acceleration of 4 m/s². What net force is required?",
    options: [
      { id: "A", text: "125 N" },
      { id: "B", text: "504 N" },
      { id: "C", text: "2,000 N" },
      { id: "D", text: "4,500 N" },
    ],
    answer: "C",
    explanation:
      "Correct! F = m × a = 500 kg × 4 m/s² = 2,000 N. This is the net force, after accounting for opposing forces.",
    lesson:
      "Newton’s second law connects net force, mass, and acceleration: F = m × a. A heavier rover needs more force for the same acceleration. A newton (N) is one kg·m/s².",
    hints: [
      "Use Newton’s second law: F = m × a.",
      "Identify mass = 500 kg and acceleration = 4 m/s². Multiply them.",
      "Calculate 500 × 4. Your answer should be in newtons (N).",
    ],
  },
  {
    mission_id: "M002",
    question_id: "Q002",
    title: "Power the outpost",
    subject: "Energy",
    context:
      "Engineer Kai needs to check the energy stored by the solar array before the long Martian night.",
    question:
      "A solar array supplies a constant 200 W for 5 hours. How much energy does it supply?",
    options: [
      { id: "A", text: "40 Wh" },
      { id: "B", text: "1,000 Wh" },
      { id: "C", text: "205 Wh" },
      { id: "D", text: "5,000 Wh" },
    ],
    answer: "B",
    explanation:
      "Correct! Energy = power × time = 200 W × 5 h = 1,000 Wh, or 1 kWh. Watts measure power; watt-hours measure energy.",
    lesson:
      "Power tells us how quickly energy is transferred. Energy = power × time. Multiplying watts by hours gives watt-hours (Wh). 1,000 Wh equals 1 kWh.",
    hints: [
      "Energy equals power multiplied by time.",
      "Power is 200 W and the time is 5 hours. Keep the time in hours to get Wh.",
      "Multiply 200 by 5. Do not divide power by time.",
    ],
  },
  {
    mission_id: "M003",
    question_id: "Q003",
    title: "Grow a greener Mars",
    subject: "Biology",
    context:
      "Dr. Noor is preparing the greenhouse. Healthy plants will help supply food and oxygen to the colony.",
    question: "Which inputs do plants use for photosynthesis?",
    options: [
      { id: "A", text: "Oxygen, sugar, and darkness" },
      { id: "B", text: "Only water and soil" },
      { id: "C", text: "Oxygen and sunlight" },
      { id: "D", text: "Carbon dioxide, water, and light" },
    ],
    answer: "D",
    explanation:
      "Correct! Photosynthesis uses light energy to turn carbon dioxide and water into sugars, releasing oxygen. Roots also need mineral nutrients for healthy growth.",
    lesson:
      "Plants capture light with chlorophyll. During photosynthesis they use carbon dioxide and water to make sugars and release oxygen. Soil provides support and minerals but is not itself an input to the photosynthesis reaction.",
    hints: [
      "Think about what enters leaves from the air and what roots absorb.",
      "Carbon dioxide enters through leaves. Water arrives from roots. What provides energy?",
      "Plants need a source of light as well as carbon dioxide and water.",
    ],
  },
];
for (const m of missions)
  fs.writeFileSync(
    `public/mock/challenge_${m.mission_id}.json`,
    JSON.stringify(m, null, 2),
  );
for (const [i, id, name, message] of [
  [
    0,
    "scientist_01",
    "Dr. Sara",
    "Welcome, explorer! Rover Beta is stuck in Sector 4. Let’s use Newton’s second law to calculate the net force it needs.",
  ],
  [
    1,
    "engineer_01",
    "Engineer Kai",
    "Good timing! We need enough stored solar energy for the night. Help me check the array’s energy output.",
  ],
  [
    2,
    "botanist_01",
    "Dr. Noor",
    "A greener Mars begins here. Help me make sure our greenhouse plants have what they need for photosynthesis.",
  ],
])
  fs.writeFileSync(
    `public/mock/dialogue_${id}.json`,
    JSON.stringify(
      {
        npc_id: id,
        npc_name: name,
        message,
        source: "offline",
        options: [
          {
            text: "Let’s solve the mission →",
            action: "START_CHALLENGE",
            payload: missions[i].mission_id,
          },
          {
            text: "Explain the science first",
            action: "EXPLAIN",
            payload: missions[i].mission_id,
          },
        ],
      },
      null,
      2,
    ),
  );
