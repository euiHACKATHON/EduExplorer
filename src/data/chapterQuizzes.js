// Chapter assessments are deliberately authored from the Grade 9 RAG units.
// Keeping answers here makes offline play possible; live assessment continues
// to use the server's protected question bank.
const q = (id, question, options, answer, explanation) => ({ id, question, options, answer, explanation });

export const chapterQuizzes = {
  M001: [
    q('U1-01','Which quantity needs both magnitude and direction?',['Distance','Speed','Velocity','Time'],'C','Velocity is a vector: it has magnitude and direction.'),
    q('U1-02','A rover travels 5 m east then 5 m west. What is its displacement?',['0 m','5 m','10 m','10 m east'],'A','It ends where it started, so its displacement is zero.'),
    q('U1-03','What is the SI unit of speed?',['m/s','m/s²','N','J'],'A','Speed is distance divided by time, measured in metres per second.'),
    q('U1-04','A rover covers 120 m in 10 s. Its average speed is:',['12 m/s','1200 m/s','12 m/s²','0.12 m/s'],'A','Speed = distance ÷ time = 120 ÷ 10 = 12 m/s.'),
    q('U1-05','What does a negative displacement show?',['The distance is smaller','Motion opposite the chosen positive direction','The rover stopped','The speed is zero'],'B','The sign gives direction, not size.'),
    q('U1-06','A craft changes velocity from 4 m/s to 16 m/s in 3 s. Its acceleration is:',['4 m/s²','12 m/s²','20 m/s²','5.3 m/s²'],'A','a = (v − u) ÷ t = (16 − 4) ÷ 3 = 4 m/s².'),
    q('U1-07','A horizontal line on a distance-time graph means the object is:',['Accelerating','Moving at constant speed','Stationary','Moving backwards'],'C','Its distance is not changing.'),
    q('U1-08','What is the net force on a 500 kg rover accelerating at 4 m/s²?',['125 N','496 N','2,000 N','20,000 N'],'C','F = m × a = 500 × 4 = 2,000 N.'),
    q('U1-09','If the net force on an object is zero, it:',['Must be stationary','Must speed up','Has no acceleration','Has no mass'],'C','Zero net force means zero acceleration; it may be stationary or move at constant velocity.'),
    q('U1-10','Newton’s third-law force pairs act:',['On the same object','On two different objects','Only when objects move','In the same direction'],'B','They are equal and opposite forces acting on different objects.')
  ],
  M002: [
    q('U2-01','The angle of incidence is measured from the:',['Mirror surface','Normal','Reflected ray','Image'],'B','Angles of incidence and reflection are measured from the normal.'),
    q('U2-02','The law of reflection states that:',['i is twice r','i equals r','i plus r is 90°','Light always bends'],'B','The angle of incidence equals the angle of reflection.'),
    q('U2-03','A plane-mirror image is:',['Real and inverted','Virtual, upright, and same size','Always smaller','Behind the object'],'B','A plane mirror forms a virtual, upright image of equal size.'),
    q('U2-04','Which mirror gives a wide field of view in a car?',['Concave','Convex','Plane','None'],'B','Convex mirrors give upright, smaller images and a wide view.'),
    q('U2-05','Light bends when entering glass because its:',['Colour changes','Speed changes','Mass increases','Direction is pulled by glass'],'B','Refraction occurs because light changes speed between media.'),
    q('U2-06','A ray travelling from air into glass bends:',['Away from the normal','Towards the normal','Into a circle','Not at all in every case'],'B','It slows in glass and bends towards the normal.'),
    q('U2-07','A convex lens is:',['Thinner in the middle and diverging','Thicker in the middle and converging','A reflecting surface','Always a mirror'],'B','A convex lens converges parallel rays.'),
    q('U2-08','A concave lens always forms an image that is:',['Real and inverted','Virtual, upright, and smaller','Real and larger','The same size'],'B','A concave lens always produces a virtual upright reduced image.'),
    q('U2-09','A magnifying glass uses a:',['Convex lens','Concave lens','Convex mirror','Plane mirror'],'A','A convex lens held inside its focal length gives a larger virtual image.'),
    q('U2-10','Short sight is corrected using a:',['Convex lens','Concave lens','Plane mirror','Concave mirror'],'B','A concave lens spreads rays so the focus moves back to the retina.')
  ],
  M003: [
    q('U3-01','In physics, work is done when a force:',['Makes you tired','Moves an object through a distance','Is very large','Acts for a long time'],'B','Work requires movement in the direction of the force.'),
    q('U3-02','What is the unit of work and energy?',['Watt','Newton','Joule','Metre per second'],'C','Work and energy transfer are measured in joules.'),
    q('U3-03','A 10 N force moves a crate 4 m in its direction. Work done is:',['2.5 J','14 J','40 J','400 J'],'C','W = F × d = 10 × 4 = 40 J.'),
    q('U3-04','Kinetic energy is the energy an object has because it is:',['Hot','Moving','High up','Charged'],'B','Kinetic energy is energy of motion.'),
    q('U3-05','As a dropped ball falls, its gravitational potential energy mainly becomes:',['Kinetic energy','Mass','Light energy','Nothing'],'A','Energy is transferred from gravitational potential to kinetic energy.'),
    q('U3-06','Power describes:',['Total energy stored','How quickly energy is transferred','The direction of a force','The mass of an object'],'B','Power is the rate of energy transfer or work done.'),
    q('U3-07','The SI unit of power is:',['Joule','Newton','Watt','Kilowatt-hour'],'C','One watt equals one joule per second.'),
    q('U3-08','A 200 W device runs for 5 hours. It uses:',['40 Wh','205 Wh','1,000 Wh','10,000 Wh'],'C','Energy = power × time = 200 W × 5 h = 1,000 Wh.'),
    q('U3-09','1,000 Wh is equal to:',['0.1 kWh','1 kWh','10 kWh','1,000 kWh'],'B','One kilowatt-hour equals 1,000 watt-hours.'),
    q('U3-10','Which statement is correct?',['Energy is used up','Power and energy are the same','Energy is transferred or transformed','A watt is a unit of energy'],'C','Energy is conserved; it changes form or transfers between stores.')
  ]
};
