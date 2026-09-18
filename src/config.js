export const WIDTH = 1120,
  HEIGHT = 680;
export const crew = [
  {
    id: "scientist_01",
    name: "Dr. Sara",
    role: "Planetary scientist",
    mission: "M001",
    x: 355,
    y: 355,
    color: 0xe9b869,
  },
  {
    id: "engineer_01",
    name: "Engineer Kai",
    role: "Systems engineer",
    mission: "M002",
    x: 815,
    y: 300,
    color: 0x85b9ba,
  },
  {
    id: "botanist_01",
    name: "Dr. Noor",
    role: "Colony botanist",
    mission: "M003",
    x: 745,
    y: 545,
    color: 0xa4bd7d,
  },
];

export const levels = [
  {
    mission: "M001",
    title: "The Aries Forge",
    objective: "Unstick the star rover",
    subject: "Physics",
    realm: "ARIES",
    subtitle: "Crimson Dunes of Motion",
    constellation: "♈",
    accent: 0xffad66,
    sky: 0x160d25,
    ground: 0x77384b,
  },
  {
    mission: "M002",
    title: "The Aquarius Circuit",
    objective: "Power the astral outpost",
    subject: "Energy",
    realm: "AQUARIUS",
    subtitle: "Electric Gardens of the Water-Bearer",
    constellation: "♒",
    accent: 0x7fe7ff,
    sky: 0x071d38,
    ground: 0x164c67,
  },
  {
    mission: "M003",
    title: "The Virgo Conservatory",
    objective: "Grow the celestial garden",
    subject: "Biology",
    realm: "VIRGO",
    subtitle: "Living Sanctuary Among the Stars",
    constellation: "♍",
    accent: 0xc7f28b,
    sky: 0x10251f,
    ground: 0x35664d,
  },
];

export function getLevel(mission) {
  return levels.findIndex((level) => level.mission === mission);
}
