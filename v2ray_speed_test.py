name: Xray Speed Test

on:
  schedule:
    - cron: '0 * * * *'  # 每小时执行一次
  workflow_dispatch: # 添加手动触发

jobs:
  speed_test:
    runs-on: ubuntu-latest

    env:
      XRAY_VERSION: "v1.8.21"  # Xray-core 的版本

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.x'

      - name: Install dependencies
        run: |
          pip install requests[socks] # 修改这里，安装 SOCKS 支持

      - name: Download Xray-core
        run: |
          wget "https://github.com/XTLS/Xray-core/releases/download/${{ env.XRAY_VERSION }}/Xray-linux-64.zip"

      - name: Unzip Xray-core
        run: |
          unzip -o Xray-linux-64.zip

      - name: Make xray executable
        run: |
           chmod +x xray

      - name: Add xray to PATH
        run: |
          echo "$(pwd)/" >> $GITHUB_PATH
          ./xray -version # 检查是否正常运行

      - name: Run speed test script
        run: python v2ray_speed_test.py

      - name: Output speed test result
        if: always()
        run: |
            echo "speed test result has finished"
