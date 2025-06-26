/**
 * RPA节点面板组件
 */
import React, { useState, useEffect } from 'react';
import { Card, Collapse, Input, Tag, Tooltip } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { RPANodeTemplate } from '@/types/api';
import { rpaService } from '@/services/rpaService';
import './NodePalette.css';

const { Panel } = Collapse;
const { Search } = Input;

interface NodePaletteProps {
  onNodeSelect: (nodeTemplate: RPANodeTemplate) => void;
}

const NodePalette: React.FC<NodePaletteProps> = ({ onNodeSelect }) => {
  const [nodeTemplates, setNodeTemplates] = useState<RPANodeTemplate[]>([]);
  const [filteredNodes, setFilteredNodes] = useState<RPANodeTemplate[]>([]);
  const [searchText, setSearchText] = useState('');
  const [loading, setLoading] = useState(true);

  // 节点分类
  const nodeCategories = [
    { key: '页面操作', color: '#1890ff' },
    { key: '键盘操作', color: '#52c41a' },
    { key: '等待操作', color: '#faad14' },
    { key: '数据获取', color: '#722ed1' },
    { key: '数据处理', color: '#eb2f96' },
    { key: '流程控制', color: '#fa541c' },
    { key: '第三方工具', color: '#13c2c2' },
    { key: '账户信息', color: '#a0d911' },
  ];

  useEffect(() => {
    loadNodeTemplates();
  }, []);

  useEffect(() => {
    filterNodes();
  }, [nodeTemplates, searchText]);

  const loadNodeTemplates = async () => {
    try {
      setLoading(true);
      const templates = await rpaService.getNodeTemplates();
      setNodeTemplates(templates);
    } catch (error) {
      console.error('Failed to load node templates:', error);
    } finally {
      setLoading(false);
    }
  };

  const filterNodes = () => {
    if (!searchText) {
      setFilteredNodes(nodeTemplates);
      return;
    }

    const filtered = nodeTemplates.filter(
      (node) =>
        node.name.toLowerCase().includes(searchText.toLowerCase()) ||
        node.description.toLowerCase().includes(searchText.toLowerCase()) ||
        node.type.toLowerCase().includes(searchText.toLowerCase())
    );
    setFilteredNodes(filtered);
  };

  const groupNodesByCategory = () => {
    const grouped: Record<string, RPANodeTemplate[]> = {};
    
    filteredNodes.forEach((node) => {
      const category = node.category || '其他';
      if (!grouped[category]) {
        grouped[category] = [];
      }
      grouped[category].push(node);
    });

    return grouped;
  };

  const getCategoryColor = (category: string) => {
    const categoryInfo = nodeCategories.find(c => c.key === category);
    return categoryInfo?.color || '#666666';
  };

  const handleNodeDragStart = (e: React.DragEvent, nodeTemplate: RPANodeTemplate) => {
    e.dataTransfer.setData('application/json', JSON.stringify(nodeTemplate));
    e.dataTransfer.effectAllowed = 'copy';
  };

  const handleNodeClick = (nodeTemplate: RPANodeTemplate) => {
    onNodeSelect(nodeTemplate);
  };

  const renderNodeItem = (nodeTemplate: RPANodeTemplate) => (
    <div
      key={nodeTemplate.type}
      className="node-item"
      draggable
      onDragStart={(e) => handleNodeDragStart(e, nodeTemplate)}
      onClick={() => handleNodeClick(nodeTemplate)}
    >
      <div className="node-header">
        <span className="node-name">{nodeTemplate.name}</span>
        <Tag 
          color={getCategoryColor(nodeTemplate.category)}
          size="small"
        >
          {nodeTemplate.type}
        </Tag>
      </div>
      <Tooltip title={nodeTemplate.description} placement="right">
        <div className="node-description">
          {nodeTemplate.description}
        </div>
      </Tooltip>
    </div>
  );

  const groupedNodes = groupNodesByCategory();

  return (
    <Card 
      title="RPA节点库" 
      size="small" 
      className="node-palette"
      extra={
        <Search
          placeholder="搜索节点..."
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          style={{ width: 200 }}
          prefix={<SearchOutlined />}
        />
      }
    >
      <div className="node-palette-content">
        <Collapse 
          defaultActiveKey={Object.keys(groupedNodes)}
          ghost
          size="small"
        >
          {Object.entries(groupedNodes).map(([category, nodes]) => (
            <Panel
              key={category}
              header={
                <div className="category-header">
                  <span>{category}</span>
                  <Tag 
                    color={getCategoryColor(category)}
                    size="small"
                  >
                    {nodes.length}
                  </Tag>
                </div>
              }
            >
              <div className="nodes-list">
                {nodes.map(renderNodeItem)}
              </div>
            </Panel>
          ))}
        </Collapse>
      </div>
    </Card>
  );
};

export default NodePalette;
