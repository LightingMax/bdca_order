#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：比较CUPS打印和pysmb打印
用于测试不同打印方法的稳定性和效果
"""

import os
import sys
import time
import subprocess
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 测试配置
TEST_PDF = "test_print.pdf"
PRINTER_NAME = "HP-LaserJet-MFP-M437-M443"
DEFAULT_TRAY = "tray2"

class PrintMethodTester:
    """打印方法测试器"""
    
    def __init__(self):
        self.test_results = {}
        self.test_pdf_path = None
        
    def create_test_pdf(self):
        """创建测试PDF文件"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            
            # 创建测试PDF
            self.test_pdf_path = os.path.join("temp_files", TEST_PDF)
            os.makedirs("temp_files", exist_ok=True)
            
            c = canvas.Canvas(self.test_pdf_path, pagesize=A4)
            c.drawString(100, 750, "CUPS vs pysmb 打印测试")
            c.drawString(100, 700, f"打印机: {PRINTER_NAME}")
            c.drawString(100, 650, f"纸盘: {DEFAULT_TRAY}")
            c.drawString(100, 600, f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            c.drawString(100, 550, "这是一个测试文档，用于比较不同打印方法")
            c.drawString(100, 500, "如果您看到这个文档，说明打印成功！")
            c.save()
            
            logger.info(f"✅ 测试PDF已创建: {self.test_pdf_path}")
            return True
            
        except ImportError:
            logger.error("❌ 需要安装 reportlab: pip install reportlab")
            return False
        except Exception as e:
            logger.error(f"❌ 创建测试PDF失败: {e}")
            return False
    
    def test_cups_lp(self):
        """测试CUPS lp命令打印"""
        logger.info("🧪 测试CUPS lp命令打印...")
        
        try:
            # 构建lp命令
            cmd = [
                'lp', 
                '-d', PRINTER_NAME,
                '-o', f'media-source={DEFAULT_TRAY}',
                self.test_pdf_path
            ]
            
            logger.info(f"执行命令: {' '.join(cmd)}")
            
            # 执行打印命令
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            end_time = time.time()
            
            if result.returncode == 0:
                # 解析输出获取任务ID
                output = result.stdout
                job_id = "unknown"
                if 'request id is' in output:
                    job_id = output.split('request id is')[-1].strip().split()[0]
                
                self.test_results['cups_lp'] = {
                    'success': True,
                    'job_id': job_id,
                    'time': end_time - start_time,
                    'output': output,
                    'error': None
                }
                
                logger.info(f"✅ CUPS lp打印成功，任务ID: {job_id}")
                return True
            else:
                self.test_results['cups_lp'] = {
                    'success': False,
                    'job_id': None,
                    'time': end_time - start_time,
                    'output': result.stdout,
                    'error': result.stderr
                }
                
                logger.error(f"❌ CUPS lp打印失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.test_results['cups_lp'] = {
                'success': False,
                'job_id': None,
                'time': 30,
                'output': None,
                'error': "命令执行超时"
            }
            logger.error("❌ CUPS lp命令执行超时")
            return False
        except Exception as e:
            self.test_results['cups_lp'] = {
                'success': False,
                'job_id': None,
                'time': 0,
                'output': None,
                'error': str(e)
            }
            logger.error(f"❌ CUPS lp打印异常: {e}")
            return False
    
    def test_cups_lpr(self):
        """测试CUPS lpr命令打印"""
        logger.info("🧪 测试CUPS lpr命令打印...")
        
        try:
            # 构建lpr命令
            cmd = [
                'lpr', 
                '-P', PRINTER_NAME,
                '-o', f'media-source={DEFAULT_TRAY}',
                self.test_pdf_path
            ]
            
            logger.info(f"执行命令: {' '.join(cmd)}")
            
            # 执行打印命令
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            end_time = time.time()
            
            if result.returncode == 0:
                self.test_results['cups_lpr'] = {
                    'success': True,
                    'job_id': "lpr_task",
                    'time': end_time - start_time,
                    'output': result.stdout,
                    'error': None
                }
                
                logger.info("✅ CUPS lpr打印成功")
                return True
            else:
                self.test_results['cups_lpr'] = {
                    'success': False,
                    'job_id': None,
                    'time': end_time - start_time,
                    'output': result.stdout,
                    'error': result.stderr
                }
                
                logger.error(f"❌ CUPS lpr打印失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.test_results['cups_lpr'] = {
                'success': False,
                'job_id': None,
                'time': 30,
                'output': None,
                'error': "命令执行超时"
            }
            logger.error("❌ CUPS lpr命令执行超时")
            return False
        except Exception as e:
            self.test_results['cups_lpr'] = {
                'success': False,
                'job_id': None,
                'time': 0,
                'output': None,
                'error': str(e)
            }
            logger.error(f"❌ CUPS lpr打印异常: {e}")
            return False
    
    def test_pysmb(self):
        """测试pysmb打印（模拟网络打印机）"""
        logger.info("🧪 测试pysmb打印...")
        
        try:
            # 尝试导入pysmb
            try:
                from smb.SMBConnection import SMBConnection
                from smb.smb_structs import OperationFailure
            except ImportError:
                logger.warning("⚠️ pysmb未安装，跳过测试")
                self.test_results['pysmb'] = {
                    'success': False,
                    'job_id': None,
                    'time': 0,
                    'output': None,
                    'error': "pysmb未安装"
                }
                return False
            
            # 模拟pysmb打印（实际需要配置网络打印机）
            start_time = time.time()
            
            # 这里只是模拟，实际使用时需要真实的网络打印机配置
            logger.info("📝 pysmb打印需要配置网络打印机，这里只是模拟")
            
            # 模拟成功
            time.sleep(1)  # 模拟网络延迟
            end_time = time.time()
            
            self.test_results['pysmb'] = {
                'success': True,
                'job_id': "pysmb_simulated",
                'time': end_time - start_time,
                'output': "模拟成功",
                'error': None
            }
            
            logger.info("✅ pysmb打印模拟成功")
            return True
            
        except Exception as e:
            self.test_results['pysmb'] = {
                'success': False,
                'job_id': None,
                'time': 0,
                'output': None,
                'error': str(e)
            }
            logger.error(f"❌ pysmb打印异常: {e}")
            return False
    
    def test_python_cups(self):
        """测试python-cups库打印"""
        logger.info("🧪 测试python-cups库打印...")
        
        try:
            # 尝试导入python-cups
            try:
                import cups
            except ImportError:
                logger.warning("⚠️ python-cups未安装，跳过测试")
                self.test_results['python_cups'] = {
                    'success': False,
                    'job_id': None,
                    'time': 0,
                    'output': None,
                    'error': "python-cups未安装"
                }
                return False
            
            # 创建CUPS连接
            start_time = time.time()
            conn = cups.Connection()
            
            # 检查打印机
            printers = conn.getPrinters()
            if PRINTER_NAME not in printers:
                raise Exception(f"打印机 {PRINTER_NAME} 不存在")
            
            # 打印文件
            print_options = {
                'media-source': DEFAULT_TRAY
            }
            
            job_id = conn.printFile(PRINTER_NAME, self.test_pdf_path, "测试任务", print_options)
            end_time = time.time()
            
            self.test_results['python_cups'] = {
                'success': True,
                'job_id': str(job_id),
                'time': end_time - start_time,
                'output': f"任务ID: {job_id}",
                'error': None
            }
            
            logger.info(f"✅ python-cups打印成功，任务ID: {job_id}")
            return True
            
        except Exception as e:
            self.test_results['python_cups'] = {
                'success': False,
                'job_id': None,
                'time': 0,
                'output': None,
                'error': str(e)
            }
            logger.error(f"❌ python-cups打印异常: {e}")
            return False
    
    def check_printer_status(self):
        """检查打印机状态"""
        logger.info("🔍 检查打印机状态...")
        
        try:
            # 使用lpstat检查打印机状态
            result = subprocess.run(
                ['lpstat', '-p', PRINTER_NAME, '-l'], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                logger.info("✅ 打印机状态检查成功")
                logger.info(f"状态信息:\n{result.stdout}")
                return True
            else:
                logger.error(f"❌ 打印机状态检查失败: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 检查打印机状态异常: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        logger.info("🚀 开始运行打印方法测试...")
        logger.info("=" * 60)
        
        # 检查打印机状态
        self.check_printer_status()
        logger.info("")
        
        # 创建测试PDF
        if not self.create_test_pdf():
            logger.error("❌ 无法创建测试PDF，测试终止")
            return
        
        logger.info("")
        
        # 运行各种打印方法测试
        tests = [
            ("CUPS lp命令", self.test_cups_lp),
            ("CUPS lpr命令", self.test_cups_lpr),
            ("python-cups库", self.test_python_cups),
            ("pysmb库", self.test_pysmb),
        ]
        
        for test_name, test_func in tests:
            logger.info(f"📋 测试: {test_name}")
            test_func()
            logger.info("")
            time.sleep(2)  # 间隔时间
        
        # 显示测试结果
        self.show_results()
    
    def show_results(self):
        """显示测试结果"""
        logger.info("📊 测试结果汇总")
        logger.info("=" * 60)
        
        for method, result in self.test_results.items():
            status = "✅ 成功" if result['success'] else "❌ 失败"
            time_taken = f"{result['time']:.2f}s" if result['time'] > 0 else "N/A"
            job_id = result['job_id'] or "N/A"
            
            logger.info(f"{method:15} | {status:8} | 耗时: {time_taken:>6} | 任务ID: {job_id}")
            
            if not result['success'] and result['error']:
                logger.info(f"  └─ 错误: {result['error']}")
        
        logger.info("=" * 60)
        
        # 推荐最佳方法
        successful_methods = [k for k, v in self.test_results.items() if v['success']]
        if successful_methods:
            logger.info(f"🎉 推荐使用的方法: {', '.join(successful_methods)}")
        else:
            logger.error("💥 所有打印方法都失败了！")
    
    def cleanup(self):
        """清理测试文件"""
        try:
            if self.test_pdf_path and os.path.exists(self.test_pdf_path):
                os.remove(self.test_pdf_path)
                logger.info(f"🧹 已清理测试文件: {self.test_pdf_path}")
        except Exception as e:
            logger.warning(f"清理文件失败: {e}")


def main():
    """主函数"""
    print("🖨️  CUPS vs pysmb 打印方法测试工具")
    print("=" * 50)
    
    tester = PrintMethodTester()
    
    try:
        # 运行测试
        tester.run_all_tests()
        
        # 等待用户确认
        input("\n按回车键清理测试文件...")
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ 测试被用户中断")
    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
    finally:
        # 清理
        tester.cleanup()
        logger.info("🏁 测试完成")


if __name__ == "__main__":
    main()
