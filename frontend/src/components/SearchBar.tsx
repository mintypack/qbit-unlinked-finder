import SearchIcon from "@mui/icons-material/Search";
import InputAdornment from "@mui/material/InputAdornment";
import TextField from "@mui/material/TextField";
import { useEffect, useState } from "react";

export function SearchBar({
  value,
  onChange,
}: {
  value: string;
  onChange: (q: string) => void;
}) {
  const [raw, setRaw] = useState(value);

  useEffect(() => {
    const t = setTimeout(() => onChange(raw), 200);
    return () => clearTimeout(t);
  }, [raw, onChange]);

  return (
    <TextField
      size="small"
      fullWidth
      placeholder="Fuzzy search downloads..."
      value={raw}
      onChange={(e) => setRaw(e.target.value)}
      slotProps={{
        input: {
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon fontSize="small" />
            </InputAdornment>
          ),
        },
      }}
    />
  );
}
