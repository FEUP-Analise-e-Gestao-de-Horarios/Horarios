import { useState } from "react";

interface Item {
  id: number;
  name: string;
  done: boolean;
}

export default function ReactTest1Page() {
  const [items, setItems] = useState<Item[]>([
    { id: 1, name: "Learn React", done: true },
    { id: 2, name: "Build something cool", done: false },
    { id: 3, name: "Deploy to production", done: false },
  ]);
  const [input, setInput] = useState("");
  const [filter, setFilter] = useState<"all" | "done" | "pending">("all");
  const count = items.filter((i) => i.done).length;

  const addItem = () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    setItems((prev) => [...prev, { id: Date.now(), name: trimmed, done: false }]);
    setInput("");
  };

  const toggleItem = (id: number) => {
    setItems((prev) => prev.map((i) => (i.id === id ? { ...i, done: !i.done } : i)));
  };

  const removeItem = (id: number) => {
    setItems((prev) => prev.filter((i) => i.id !== id));
  };

  const filtered = items.filter((i) => {
    if (filter === "done") return i.done;
    if (filter === "pending") return !i.done;
    return true;
  });

  return (
    <div className="max-w-lg mx-auto mt-10 p-6 font-sans">
      <h1 className="text-2xl font-bold mb-1">React Test Page</h1>
      <p className="text-gray-500 mb-4">
        {count} / {items.length} completed
      </p>

      <div className="flex gap-2 mb-4">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && addItem()}
          placeholder="New item..."
          className="flex-1 px-3 py-1.5 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <button
          onClick={addItem}
          className="px-4 py-1.5 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Add
        </button>
      </div>

      <div className="flex gap-2 mb-4">
        {(["all", "done", "pending"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1 rounded capitalize text-sm ${filter === f ? "bg-gray-800 text-white font-semibold" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
          >
            {f}
          </button>
        ))}
      </div>

      <ul className="space-y-2">
        {filtered.map((item) => (
          <li key={item.id} className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={item.done}
              onChange={() => toggleItem(item.id)}
              className="w-4 h-4"
            />
            <span className={`flex-1 ${item.done ? "line-through text-gray-400" : ""}`}>
              {item.name}
            </span>
            <button
              onClick={() => removeItem(item.id)}
              className="text-gray-400 hover:text-red-500"
            >
              ✕
            </button>
          </li>
        ))}
        {filtered.length === 0 && <li className="text-gray-400">No items.</li>}
      </ul>
    </div>
  );
}
