import type { Tag } from '../../types';
import './TagChip.css';

interface TagChipProps {
  tag: Tag;
}

function TagChip({ tag }: TagChipProps) {
  return (
    <span
      className="tag-chip-display"
      style={{
        backgroundColor: `${tag.color}20`,
        color: tag.color,
        borderColor: `${tag.color}40`,
      }}
    >
      <span className="tag-chip-dot" style={{ backgroundColor: tag.color }} />
      {tag.name}
    </span>
  );
}

export default TagChip;
