import { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2 } from 'lucide-react';
import { getTags, createTag, updateTag, deleteTag } from '../../api/client';
import type { Tag } from '../../types';
import { useAppData } from '../../state/useAppData';
import './TagManager.css';

function TagManager() {
  const [tags, setTags] = useState<Tag[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editingTag, setEditingTag] = useState<Tag | null>(null);
  const [formData, setFormData] = useState({ name: '', color: '#6366f1' });
  const [loading, setLoading] = useState(false);
  const { refresh, toast } = useAppData();

  useEffect(() => {
    loadTags();
  }, []);

  const loadTags = async () => {
    try {
      const data = await getTags();
      setTags(data);
    } catch (error) {
      console.error('Failed to load tags:', error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (editingTag) {
        await updateTag(editingTag.id, formData);
      } else {
        await createTag(formData);
      }
      await loadTags();
      await refresh(); // the sidebar groups companies by tag
      resetForm();
    } catch (error) {
      console.error('Failed to save tag:', error);
      toast('Failed to save tag', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (tagId: string) => {
    if (!confirm('Delete this tag? Companies keep their data; they just lose the tag.')) return;

    try {
      await deleteTag(tagId);
      await loadTags();
      await refresh();
    } catch (error) {
      console.error('Failed to delete tag:', error);
      toast('Failed to delete tag', 'error');
    }
  };

  const handleEdit = (tag: Tag) => {
    setEditingTag(tag);
    setFormData({ name: tag.name, color: tag.color });
    setShowForm(true);
  };

  const resetForm = () => {
    setFormData({ name: '', color: '#6366f1' });
    setEditingTag(null);
    setShowForm(false);
  };

  return (
    <div className="tag-manager">
      <div className="tag-manager-header">
        <h2>Tag Management</h2>
        {!showForm && (
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>
            <Plus size={16} />
            New Tag
          </button>
        )}
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="tag-form">
          <div className="tag-form-fields">
            <input
              type="text"
              placeholder="Tag name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
            <div className="color-picker">
              <input
                type="color"
                value={formData.color}
                onChange={(e) => setFormData({ ...formData, color: e.target.value })}
              />
              <span>{formData.color}</span>
            </div>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Saving...' : editingTag ? 'Update' : 'Create'}
            </button>
            <button type="button" className="btn btn-secondary" onClick={resetForm}>
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="tag-list">
        {tags.map((tag) => (
          <div key={tag.id} className="tag-item">
            <div className="tag-info">
              <span className="tag-color" style={{ backgroundColor: tag.color }} />
              <span className="tag-name">{tag.name}</span>
            </div>
            <div className="tag-actions">
              <button
                className="icon-button"
                onClick={() => handleEdit(tag)}
                title="Edit"
              >
                <Edit2 size={16} />
              </button>
              <button
                className="icon-button"
                onClick={() => handleDelete(tag.id)}
                title="Delete"
              >
                <Trash2 size={16} />
              </button>
            </div>
          </div>
        ))}
        {tags.length === 0 && (
          <div className="empty-tags">
            No tags yet. Create one to get started!
          </div>
        )}
      </div>
    </div>
  );
}

export default TagManager;
