
import React, { useState, useCallback } from 'react';
import { Upload, Image, DollarSign, FileSpreadsheet, Zap, Globe, Calculator, Download } from 'lucide-react';

const CURRENCY_SYMBOLS = {
  USD: '$', EUR: '€', GBP: '£', SAR: 'SAR', KRW: '₩', AED: 'AED'
};

const DEFAULT_EXCHANGE_RATES = {
  USD: 1,
  EUR: 0.92,
  GBP: 0.79,
  SAR: 3.75,
  KRW: 1320,
  AED: 3.67
};

const COUNTRY_CODES = {
  US: { currency: 'USD', flag: '🇺🇸', name: 'United States' },
  FR: { currency: 'EUR', flag: '🇫🇷', name: 'France' },
  DE: { currency: 'EUR', flag: '🇩🇪', name: 'Germany' },
  ES: { currency: 'EUR', flag: '🇪🇸', name: 'Spain' },
  SA: { currency: 'SAR', flag: '🇸🇦', name: 'Saudi Arabia' },
  KR: { currency: 'KRW', flag: '🇰🇷', name: 'South Korea' },
  AE: { currency: 'AED', flag: '🇦🇪', name: 'UAE' }
};

export default function AliExpressPromoMatcher() {
  const [promoTiers, setPromoTiers] = useState([]);
  const [productPrice, setProductPrice] = useState('');
  const [productCurrency, setProductCurrency] = useState('USD');
  const [exchangeRates, setExchangeRates] = useState(DEFAULT_EXCHANGE_RATES);
  const [matchResults, setMatchResults] = useState(null);
  const [promoFile, setPromoFile] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // 解析促销档位文件（Excel/CSV）
  const parsePromoFile = async (file) => {
    setIsAnalyzing(true);
    const reader = new FileReader();
    
    reader.onload = async (e) => {
      const text = e.target.result;
      
      // 简单的CSV解析
      if (file.name.endsWith('.csv')) {
        const lines = text.split('\n');
        const tiers = [];
        
        lines.slice(1).forEach(line => {
          const parts = line.split(',').map(s => s.trim());
          if (parts.length >= 4) {
            tiers.push({
              country: parts[0],
              currency: parts[1],
              threshold: parseFloat(parts[2]),
              discount: parseFloat(parts[3]),
              code: parts[4] || ''
            });
          }
        });
        
        setPromoTiers(tiers);
      }
      
      setIsAnalyzing(false);
    };
    
    reader.readAsText(file);
  };

  // 使用Claude API分析促销图片
  const analyzePromoImage = async (file) => {
    setIsAnalyzing(true);
    
    try {
      const base64 = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });

      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 1000,
          messages: [{
            role: 'user',
            content: [
              {
                type: 'image',
                source: { type: 'base64', media_type: 'image/png', data: base64 }
              },
              {
                type: 'text',
                text: `分析这张AliExpress促销图片，提取所有促销档位信息。
                
请以JSON格式返回，不要包含markdown代码块标记：
[
  {
    "country": "国家代码（如US, FR, SA等）",
    "currency": "货币代码（如USD, EUR, SAR等）",
    "threshold": 门槛金额（数字）,
    "discount": 优惠金额（数字）,
    "code": "优惠码"
  }
]

提取图片中所有可见的促销档位。`
              }
            ]
          }]
        })
      });

      const data = await response.json();
      const text = data.content.find(c => c.type === 'text')?.text || '';
      
      // 清理可能的markdown标记
      const cleanText = text.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
      const tiers = JSON.parse(cleanText);
      
      setPromoTiers(tiers);
    } catch (error) {
      console.error('分析图片失败:', error);
      alert('图片分析失败，请尝试手动上传CSV文件或检查图片格式');
    }
    
    setIsAnalyzing(false);
  };

  // 分析产品价格图片
  const analyzeProductImage = async (file) => {
    setIsAnalyzing(true);
    
    try {
      const base64 = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });

      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 1000,
          messages: [{
            role: 'user',
            content: [
              {
                type: 'image',
                source: { type: 'base64', media_type: 'image/png', data: base64 }
              },
              {
                type: 'text',
                text: `识别这张产品图片中的价格。只返回JSON格式，不要包含其他文字：
{
  "price": 数字金额,
  "currency": "货币代码（USD/EUR/GBP等）"
}`
              }
            ]
          }]
        })
      });

      const data = await response.json();
      const text = data.content.find(c => c.type === 'text')?.text || '';
      const cleanText = text.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
      const result = JSON.parse(cleanText);
      
      setProductPrice(result.price.toString());
      setProductCurrency(result.currency);
    } catch (error) {
      console.error('识别价格失败:', error);
      alert('价格识别失败，请手动输入');
    }
    
    setIsAnalyzing(false);
  };

  // 计算最优档位匹配
  const calculateMatches = () => {
    if (!productPrice || promoTiers.length === 0) {
      alert('请先输入产品价格并上传促销档位信息');
      return;
    }

    const price = parseFloat(productPrice);
    const results = {};

    // 按国家分组
    const tiersByCountry = {};
    promoTiers.forEach(tier => {
      if (!tiersByCountry[tier.country]) {
        tiersByCountry[tier.country] = [];
      }
      tiersByCountry[tier.country].push(tier);
    });

    // 为每个国家计算最优档位
    Object.entries(tiersByCountry).forEach(([country, tiers]) => {
      const currencyCode = tiers[0].currency;
      const convertedPrice = price * (exchangeRates[productCurrency] / exchangeRates[currencyCode]);
      
      // 找到所有满足条件的档位
      const validTiers = tiers
        .filter(t => convertedPrice >= t.threshold)
        .sort((a, b) => b.discount - a.discount);

      if (validTiers.length > 0) {
        const bestTier = validTiers[0];
        results[country] = {
          ...bestTier,
          convertedPrice,
          finalPrice: convertedPrice - bestTier.discount,
          savings: bestTier.discount
        };
      }
    });

    // 选择前6个最优国家
    const topCountries = Object.entries(results)
      .sort((a, b) => b[1].savings - a[1].savings)
      .slice(0, 6)
      .reduce((acc, [country, data]) => {
        acc[country] = data;
        return acc;
      }, {});

    setMatchResults(topCountries);
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: '2rem',
      fontFamily: '"Space Grotesk", -apple-system, sans-serif'
    }}>
      <div style={{
        maxWidth: '1400px',
        margin: '0 auto'
      }}>
        {/* Header */}
        <div style={{
          textAlign: 'center',
          marginBottom: '3rem',
          color: 'white'
        }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '1rem',
            marginBottom: '1rem'
          }}>
            <Zap size={48} strokeWidth={2.5} />
            <h1 style={{
              fontSize: '3rem',
              fontWeight: '800',
              margin: 0,
              letterSpacing: '-0.02em'
            }}>
              AliExpress 促销码智能匹配器
            </h1>
          </div>
          <p style={{
            fontSize: '1.25rem',
            opacity: 0.9,
            maxWidth: '600px',
            margin: '0 auto'
          }}>
            自动识别价格、计算汇率、匹配最优档位，让跨境促销轻松搞定
          </p>
        </div>

        {/* Main Content */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '2rem',
          marginBottom: '2rem'
        }}>
          {/* 左侧：上传区域 */}
          <div style={{
            background: 'white',
            borderRadius: '1rem',
            padding: '2rem',
            boxShadow: '0 20px 60px rgba(0,0,0,0.3)'
          }}>
            <h2 style={{
              fontSize: '1.5rem',
              fontWeight: '700',
              marginBottom: '1.5rem',
              color: '#1a1a2e'
            }}>
              📊 促销档位设置
            </h2>

            {/* 促销档位上传 */}
            <div style={{
              border: '2px dashed #667eea',
              borderRadius: '0.75rem',
              padding: '2rem',
              textAlign: 'center',
              marginBottom: '1.5rem',
              background: '#f8f9ff',
              cursor: 'pointer',
              transition: 'all 0.3s'
            }}
            onDragOver={(e) => {
              e.preventDefault();
              e.currentTarget.style.borderColor = '#764ba2';
              e.currentTarget.style.background = '#f0f0ff';
            }}
            onDragLeave={(e) => {
              e.currentTarget.style.borderColor = '#667eea';
              e.currentTarget.style.background = '#f8f9ff';
            }}
            onDrop={(e) => {
              e.preventDefault();
              const file = e.dataTransfer.files[0];
              if (file) {
                setPromoFile(file);
                if (file.type.includes('image')) {
                  analyzePromoImage(file);
                } else {
                  parsePromoFile(file);
                }
              }
              e.currentTarget.style.borderColor = '#667eea';
              e.currentTarget.style.background = '#f8f9ff';
            }}>
              <input
                type="file"
                id="promoUpload"
                accept=".csv,.xlsx,.xls,.png,.jpg,.jpeg"
                style={{ display: 'none' }}
                onChange={(e) => {
                  const file = e.target.files[0];
                  if (file) {
                    setPromoFile(file);
                    if (file.type.includes('image')) {
                      analyzePromoImage(file);
                    } else {
                      parsePromoFile(file);
                    }
                  }
                }}
              />
              <label htmlFor="promoUpload" style={{ cursor: 'pointer' }}>
                <FileSpreadsheet size={48} color="#667eea" style={{ marginBottom: '1rem' }} />
                <p style={{ fontWeight: '600', marginBottom: '0.5rem', color: '#1a1a2e' }}>
                  上传促销档位表
                </p>
                <p style={{ fontSize: '0.875rem', color: '#666' }}>
                  支持 CSV、Excel 或图片格式
                </p>
                {promoFile && (
                  <p style={{ marginTop: '1rem', color: '#667eea', fontWeight: '600' }}>
                    ✓ {promoFile.name}
                  </p>
                )}
              </label>
            </div>

            {/* 产品价格输入 */}
            <h2 style={{
              fontSize: '1.5rem',
              fontWeight: '700',
              marginBottom: '1.5rem',
              marginTop: '2rem',
              color: '#1a1a2e'
            }}>
              💰 产品价格
            </h2>

            {/* 图片识别价格 */}
            <div style={{
              border: '2px dashed #667eea',
              borderRadius: '0.75rem',
              padding: '2rem',
              textAlign: 'center',
              marginBottom: '1.5rem',
              background: '#f8f9ff',
              cursor: 'pointer'
            }}>
              <input
                type="file"
                id="productImageUpload"
                accept="image/*"
                style={{ display: 'none' }}
                onChange={(e) => {
                  const file = e.target.files[0];
                  if (file) analyzeProductImage(file);
                }}
              />
              <label htmlFor="productImageUpload" style={{ cursor: 'pointer' }}>
                <Image size={40} color="#667eea" style={{ marginBottom: '0.75rem' }} />
                <p style={{ fontWeight: '600', fontSize: '0.95rem', color: '#1a1a2e' }}>
                  上传产品图片自动识别价格
                </p>
              </label>
            </div>

            {/* 手动输入价格 */}
            <div style={{ display: 'flex', gap: '1rem' }}>
              <div style={{ flex: 1 }}>
                <label style={{
                  display: 'block',
                  marginBottom: '0.5rem',
                  fontWeight: '600',
                  color: '#1a1a2e'
                }}>
                  产品价格
                </label>
                <input
                  type="number"
                  value={productPrice}
                  onChange={(e) => setProductPrice(e.target.value)}
                  placeholder="75.00"
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '2px solid #e0e0e0',
                    borderRadius: '0.5rem',
                    fontSize: '1rem',
                    fontFamily: 'inherit'
                  }}
                />
              </div>
              <div style={{ width: '120px' }}>
                <label style={{
                  display: 'block',
                  marginBottom: '0.5rem',
                  fontWeight: '600',
                  color: '#1a1a2e'
                }}>
                  货币
                </label>
                <select
                  value={productCurrency}
                  onChange={(e) => setProductCurrency(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '2px solid #e0e0e0',
                    borderRadius: '0.5rem',
                    fontSize: '1rem',
                    fontFamily: 'inherit'
                  }}
                >
                  {Object.keys(CURRENCY_SYMBOLS).map(curr => (
                    <option key={curr} value={curr}>{curr}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* 计算按钮 */}
            <button
              onClick={calculateMatches}
              disabled={isAnalyzing}
              style={{
                width: '100%',
                marginTop: '2rem',
                padding: '1rem',
                background: isAnalyzing ? '#ccc' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: 'white',
                border: 'none',
                borderRadius: '0.75rem',
                fontSize: '1.1rem',
                fontWeight: '700',
                cursor: isAnalyzing ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
                transition: 'transform 0.2s',
                fontFamily: 'inherit'
              }}
              onMouseEnter={(e) => !isAnalyzing && (e.currentTarget.style.transform = 'scale(1.02)')}
              onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
            >
              <Calculator size={20} />
              {isAnalyzing ? '分析中...' : '开始计算匹配'}
            </button>
          </div>

          {/* 右侧：档位信息预览 */}
          <div style={{
            background: 'white',
            borderRadius: '1rem',
            padding: '2rem',
            boxShadow: '0 20px 60px rgba(0,0,0,0.3)'
          }}>
            <h2 style={{
              fontSize: '1.5rem',
              fontWeight: '700',
              marginBottom: '1.5rem',
              color: '#1a1a2e'
            }}>
              📋 已加载档位 ({promoTiers.length})
            </h2>
            
            <div style={{
              maxHeight: '500px',
              overflowY: 'auto',
              background: '#f8f9ff',
              borderRadius: '0.5rem',
              padding: '1rem'
            }}>
              {promoTiers.length === 0 ? (
                <p style={{ textAlign: 'center', color: '#666', padding: '2rem' }}>
                  暂无档位数据，请上传促销档位表
                </p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {promoTiers.map((tier, idx) => (
                    <div key={idx} style={{
                      background: 'white',
                      padding: '1rem',
                      borderRadius: '0.5rem',
                      border: '1px solid #e0e0e0',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}>
                      <div>
                        <div style={{ fontWeight: '600', marginBottom: '0.25rem' }}>
                          {COUNTRY_CODES[tier.country]?.flag || '🌍'} {tier.country}
                        </div>
                        <div style={{ fontSize: '0.875rem', color: '#666' }}>
                          满 {tier.threshold} {tier.currency} 减 {tier.discount}
                        </div>
                      </div>
                      <div style={{
                        background: '#667eea',
                        color: 'white',
                        padding: '0.25rem 0.75rem',
                        borderRadius: '0.25rem',
                        fontSize: '0.875rem',
                        fontWeight: '600'
                      }}>
                        {tier.code}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 匹配结果 */}
        {matchResults && (
          <div style={{
            background: 'white',
            borderRadius: '1rem',
            padding: '2rem',
            boxShadow: '0 20px 60px rgba(0,0,0,0.3)'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '2rem'
            }}>
              <h2 style={{
                fontSize: '1.75rem',
                fontWeight: '700',
                color: '#1a1a2e',
                margin: 0
              }}>
                🎯 最优匹配结果
              </h2>
              <button
                onClick={() => {
                  const text = Object.entries(matchResults)
                    .map(([country, data]) => 
                      `${COUNTRY_CODES[country]?.flag || ''} ${country}: ${data.code} (${data.currency} ${data.threshold}-${data.discount})`
                    ).join('\n');
                  navigator.clipboard.writeText(text);
                  alert('已复制到剪贴板！');
                }}
                style={{
                  padding: '0.75rem 1.5rem',
                  background: '#667eea',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.5rem',
                  fontWeight: '600',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontFamily: 'inherit'
                }}
              >
                <Download size={18} />
                复制结果
              </button>
            </div>

            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: '1.5rem'
            }}>
              {Object.entries(matchResults).map(([country, data]) => (
                <div key={country} style={{
                  background: 'linear-gradient(135deg, #667eea15 0%, #764ba215 100%)',
                  borderRadius: '0.75rem',
                  padding: '1.5rem',
                  border: '2px solid #667eea30'
                }}>
                  <div style={{
                    fontSize: '2.5rem',
                    marginBottom: '0.5rem'
                  }}>
                    {COUNTRY_CODES[country]?.flag || '🌍'}
                  </div>
                  <div style={{
                    fontSize: '1.25rem',
                    fontWeight: '700',
                    marginBottom: '0.5rem',
                    color: '#1a1a2e'
                  }}>
                    {country}
                  </div>
                  <div style={{
                    display: 'inline-block',
                    background: '#667eea',
                    color: 'white',
                    padding: '0.5rem 1rem',
                    borderRadius: '0.5rem',
                    fontSize: '1.1rem',
                    fontWeight: '700',
                    marginBottom: '1rem'
                  }}>
                    {data.code}
                  </div>
                  <div style={{
                    fontSize: '0.875rem',
                    color: '#666',
                    lineHeight: '1.6'
                  }}>
                    <div>价格: {data.convertedPrice.toFixed(2)} {data.currency}</div>
                    <div>门槛: {data.threshold} {data.currency}</div>
                    <div>优惠: -{data.discount} {data.currency}</div>
                    <div style={{
                      marginTop: '0.5rem',
                      fontWeight: '700',
                      color: '#667eea',
                      fontSize: '1rem'
                    }}>
                      实付: {data.finalPrice.toFixed(2)} {data.currency}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 汇率设置（可选折叠区域） */}
        <details style={{
          marginTop: '2rem',
          background: 'white',
          borderRadius: '1rem',
          padding: '1.5rem',
          boxShadow: '0 10px 30px rgba(0,0,0,0.2)'
        }}>
          <summary style={{
            cursor: 'pointer',
            fontWeight: '700',
            fontSize: '1.1rem',
            color: '#1a1a2e',
            userSelect: 'none'
          }}>
            ⚙️ 高级设置：自定义汇率
          </summary>
          <div style={{
            marginTop: '1.5rem',
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '1rem'
          }}>
            {Object.entries(exchangeRates).map(([currency, rate]) => (
              <div key={currency}>
                <label style={{
                  display: 'block',
                  marginBottom: '0.5rem',
                  fontWeight: '600',
                  color: '#1a1a2e'
                }}>
                  {currency} 汇率
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={rate}
                  onChange={(e) => setExchangeRates({
                    ...exchangeRates,
                    [currency]: parseFloat(e.target.value) || 1
                  })}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '2px solid #e0e0e0',
                    borderRadius: '0.5rem',
                    fontSize: '1rem',
                    fontFamily: 'inherit'
                  }}
                />
              </div>
            ))}
          </div>
        </details>
      </div>
    </div>
  );
}
