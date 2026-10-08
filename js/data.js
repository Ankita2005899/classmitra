// Change the site name here. It is used everywhere in the dashboard.
const SITE = { name: "ClassMitra", tagline: "Your AI classroom assistant" };

// SAMPLE DATA: replace with your own departments, subjects and teachers.
// Later this will come from the backend (GET /api/departments).
const YEARS = [
  { id: "fe", short: "FE", full: "First Year",  students: 64 },
  { id: "se", short: "SE", full: "Second Year", students: 60 },
  { id: "te", short: "TE", full: "Third Year",  students: 58 },
  { id: "be", short: "BE", full: "Final Year",  students: 52 },
];
const TEACHERS = ["Prof. A. Kulkarni", "Prof. S. Deshmukh", "Prof. R. Patil", "Prof. M. Joshi", "Prof. N. Shinde", "Prof. P. More"];
const slug = (t) => t.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

function dept(id, code, name, subjectsByYear) {
  return {
    id, code, name,
    classes: YEARS.map((y, yi) => ({
      id: y.id, name: y.short, full: y.full,
      divisions: ["A", "B"].map((d, di) => ({
        id: d.toLowerCase(), name: "Division " + d, students: y.students - di * 2,
        subjects: subjectsByYear[yi].map((s, si) => ({
          id: slug(s), name: s,
          teacher: TEACHERS[(yi + si + di) % TEACHERS.length],
          lessons: 4 + si * 3 + yi,
        })),
      })),
    })),
  };
}

const DATA = [
  dept("comp", "COMP", "Computer Engineering", [
    ["Engineering Mathematics", "Basic Electronics", "Programming Fundamentals"],
    ["Data Structures", "Discrete Mathematics", "Computer Organization"],
    ["Machine Learning", "Database Systems", "Operating Systems"],
    ["Deep Learning", "Distributed Systems", "Cloud Computing"],
  ]),
  dept("it", "IT", "Information Technology", [
    ["Engineering Physics", "Basic Electronics", "Programming Fundamentals"],
    ["Data Structures", "Digital Electronics", "Object Oriented Programming"],
    ["Data Science", "Computer Networks", "Software Engineering"],
    ["Information Security", "Big Data Analytics", "Cloud Computing"],
  ]),
  dept("entc", "E&TC", "Electronics and Telecommunication", [
    ["Engineering Mathematics", "Basic Electronics", "Engineering Graphics"],
    ["Signals and Systems", "Analog Circuits", "Network Theory"],
    ["Digital Communication", "Microcontrollers", "Control Systems"],
    ["VLSI Design", "Wireless Networks", "Embedded Systems"],
  ]),
  dept("mech", "MECH", "Mechanical Engineering", [
    ["Engineering Mechanics", "Engineering Physics", "Engineering Graphics"],
    ["Thermodynamics", "Fluid Mechanics", "Strength of Materials"],
    ["Heat Transfer", "Machine Design", "Manufacturing Processes"],
    ["CAD/CAM", "Refrigeration and AC", "Industrial Engineering"],
  ]),
];
