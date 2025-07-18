import { useState } from "react";

type Player = {
  name: string;
  rawScore: number;
  rank: number;
  finalScore: number;
};

function App() {
  const [players, setPlayers] = useState<Player[]>([
    { name: "A", rawScore: 0, rank: 0, finalScore: 0 },
    { name: "B", rawScore: 0, rank: 0, finalScore: 0 },
    { name: "C", rawScore: 0, rank: 0, finalScore: 0 },
    { name: "D", rawScore: 0, rank: 0, finalScore: 0 },
  ]);

  const UMA = [15, 5, -5, -15]; // 1位〜4位
  const OKA = 20;
  const RATE = 100;

  const handleScoreChange = (index: number, value: number) => {
    const updated = [...players];
    updated[index].rawScore = value;
    setPlayers(updated);
  };

  const calculate = () => {
    const sorted = [...players].sort((a, b) => b.rawScore - a.rawScore);
    sorted.forEach((p, i) => {
      p.rank = i + 1;
      const diff = (p.rawScore - 25000) / 1000;
      const final = diff + UMA[i] + OKA / 4;
      p.finalScore = Math.round(final * RATE);
    });
    setPlayers([...sorted]);
  };

  return (
    <div className="p-4 max-w-xl mx-auto">
      <h1 className="text-xl font-bold mb-4">麻雀スコア計算</h1>
      {players.map((p, i) => (
        <div key={i} className="mb-2 flex gap-2 items-center">
          <label className="w-6">{p.name}</label>
          <input
            type="number"
            value={p.rawScore}
            onChange={(e) => handleScoreChange(i, parseInt(e.target.value || "0", 10))}
            className="border px-2 py-1 w-24"
          />
          <span>順位: {p.rank || "-"}</span>
          <span>→ スコア: {p.finalScore || "-"}</span>
        </div>
      ))}
      <button onClick={calculate} className="mt-4 bg-blue-500 text-white px-4 py-2 rounded">
        計算
      </button>
    </div>
  );
}

export default App;
