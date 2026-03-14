import { useState, useEffect } from "react";

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
  const [count, setCount] = useState(0);

  useEffect(() => {
    setCount(items.filter((i) => i.done).length);
  }, [items]);

  const addItem = () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    setItems((prev) => [
      ...prev,
      { id: Date.now(), name: trimmed, done: false },
    ]);
    setInput("");
  };

  const toggleItem = (id: number) => {
    setItems((prev) =>
      prev.map((i) => (i.id === id ? { ...i, done: !i.done } : i)),
    );
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
    <div
      style={{ maxWidth: 480, margin: "40px auto", fontFamily: "sans-serif" }}
    >
      <h1>React Test Page</h1>
      <p>
        {count} / {items.length} completed
      </p>

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && addItem()}
          placeholder="New item..."
          style={{ flex: 1, padding: "6px 10px" }}
        />
        <button onClick={addItem}>Add</button>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        {(["all", "done", "pending"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{ fontWeight: filter === f ? "bold" : "normal" }}
          >
            {f}
          </button>
        ))}
      </div>

      <ul style={{ listStyle: "none", padding: 0 }}>
        {filtered.map((item) => (
          <li
            key={item.id}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginBottom: 8,
            }}
          >
            <input
              type="checkbox"
              checked={item.done}
              onChange={() => toggleItem(item.id)}
            />
            <span
              style={{
                flex: 1,
                textDecoration: item.done ? "line-through" : "none",
              }}
            >
              {item.name}
            </span>
            <button onClick={() => removeItem(item.id)}>✕</button>
          </li>
        ))}
        {filtered.length === 0 && <li style={{ color: "#999" }}>No items.</li>}
      </ul>
    </div>
  );
}
