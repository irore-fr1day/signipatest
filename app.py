import os
import subprocess
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "7333361907:AAFscxsmq1Kt-lcJs2JVOzoBjzxJ1LL6VOI"
ZSIGN_PATH = "/zsign/build/zsign"

async def signipa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Отправьте P12 сертификат.")
    context.user_data['action'] = 'get_p12_certificate'

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    action = context.user_data.get('action')
    document = update.message.document

    if action == 'get_p12_certificate':
        await document.download('certificate.p12')  # Correct method to download
        await update.message.reply_text("Отправьте пароль для P12 сертификата.")
        context.user_data['action'] = 'get_p12_password'

    elif action == 'get_p12_password':
        context.user_data['p12_password'] = update.message.text
        await update.message.reply_text("Отправьте .mobileprovision файл.")
        context.user_data['action'] = 'get_mobileprovision'

    elif action == 'get_mobileprovision':
        await document.download('profile.mobileprovision')  # Correct method to download
        await update.message.reply_text("Отправьте IPA файл для подписания.")
        context.user_data['action'] = 'get_ipa'

    elif action == 'get_ipa':
        await document.download('app.ipa')  # Correct method to download
        await update.message.reply_text("Введите новый BundleID.")
        context.user_data['action'] = 'get_bundle_id'

    elif action == 'get_bundle_id':
        context.user_data['bundle_id'] = update.message.text
        await update.message.reply_text("Подписываю IPA файл, пожалуйста, подождите...")
        
        # Запуск подписания
        signed_ipa_path = sign_ipa('certificate.p12', context.user_data['p12_password'], 'profile.mobileprovision', 'app.ipa', context.user_data['bundle_id'])
        
        if signed_ipa_path:
            plist_path, plist_link = create_plist(signed_ipa_path, context.user_data['bundle_id'])
            await update.message.reply_text(f"Ваш файл подписан. Установите его через ссылку:\n{plist_link}")
        else:
            await update.message.reply_text("Ошибка при подписании файла.")
        
        # Очистка временных файлов
        clean_up_temp_files()
        context.user_data.clear()

def sign_ipa(p12_path, p12_password, mobileprovision_path, ipa_path, bundle_id):
    signed_ipa_path = "signed_app.ipa"
    command = [
        ZSIGN_PATH, "-p", p12_path, "-w", p12_password, "-m", mobileprovision_path,
        "-o", signed_ipa_path, "-b", bundle_id, ipa_path
    ]
    try:
        subprocess.run(command, check=True)
        return signed_ipa_path
    except subprocess.CalledProcessError:
        return None

def create_plist(ipa_path, bundle_id):
    plist_path = "install.plist"
    ipa_link = f"https://your-heroku-app.herokuapp.com/files/{ipa_path}"
    
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
    <plist version="1.0">
        <dict>
            <key>items</key>
            <array>
                <dict>
                    <key>assets</key>
                    <array>
                        <dict>
                            <key>kind</key>
                            <string>software-package</string>
                            <key>url</key>
                            <string>{ipa_link}</string>
                        </dict>
                    </array>
                    <key>metadata</key>
                    <dict>
                        <key>bundle-identifier</key>
                        <string>{bundle_id}</string>
                        <key>bundle-version</key>
                        <string>1.0.0</string>
                        <key>kind</key>
                        <string>software</string>
                        <key>title</key>
                        <string>SignedApp</string>
                    </dict>
                </dict>
            </array>
        </dict>
    </plist>
    """
    with open(plist_path, "w") as plist_file:
        plist_file.write(plist_content)
    
    plist_link = f"https://signipatest.herokuapp.com/files/{plist_path}"
    return plist_path, plist_link

def clean_up_temp_files():
    files = ['certificate.p12', 'profile.mobileprovision', 'app.ipa', 'signed_app.ipa', 'install.plist']
    for file in files:
        if os.path.exists(file):
            os.remove(file)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Этот текст не распознан как команда или документ.")

def main():
    application = Application.builder().token(TOKEN).build()
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("signipa", signipa))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()
