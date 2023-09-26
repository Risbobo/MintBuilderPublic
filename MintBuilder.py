from aiogram import Bot, Dispatcher, executor, types
import random
import time
import math
import sys

WARNING_THRESHOLD = 12
MAX_PER_TEAM = 6
REC = "Receive command : "
NO_NAME = "X"

with open("config.txt", 'r') as file:
    frst_line = file.readline()
    scnd_line = file.readline()
    thrd_line = file.readline()
    # Keys : chat_id, Values : (poll_id, message_id)
    polls = eval(frst_line)
    # Keys : poll_id, Values : [(participant_first_name, participant_last_name)]
    participants_per_poll = eval(scnd_line)
    bot_token = thrd_line

bot = Bot(token=bot_token)
dp = Dispatcher(bot)


print("I'm listening")


# Return True if two participants have the same first name
def homonym_check(participants):
    first_names = [participant[0] for participant in participants]
    unique_first_names = set(first_names)
    return len(first_names) != len(unique_first_names)


def shuffle_with_constraints(participants, constraints):
    # Set up variables
    n = math.ceil(len(participants) / 6)
    teams = [[] for _ in range(n)]
    teams_size = [math.floor(len(participants) / n) for _ in range(n)]
    for i in range(len(participants) % n):
        teams_size[i] += 1
    # Set up constraints and participants
    constraints.sort(key=len)
    constraints.reverse()
    for u in participants:
        if not any(u in sub_list for sub_list in constraints):
            constraints.append([u])
    # Generate the teams randomly
    for cons in constraints:
        possible_team = [x for x in range(n)]
        while len(possible_team) > 0:
            random.shuffle(possible_team)
            selected_team = possible_team[0]
            if len(teams[selected_team]) + len(cons) > teams_size[selected_team]:
                possible_team.remove(selected_team)
            else:
                teams[selected_team] += cons
                break
        if len(possible_team) == 0:
            print('Problem')
    # Format the generated teams
    team_text = []
    if homonym_check(participants):
        for i, team in enumerate(teams):
            team_text.append("*Equipe {}*".format(i + 1))
            for member in team:
                team_text.append('- {} {}'.format(member[0], member[1]))
            team_text.append('')
    else:
        for i, team in enumerate(teams):
            team_text.append("*Equipe {}*".format(i + 1))
            for member in team:
                team_text.append('- {}'.format(member[0]))
            team_text.append('')
    team_text.append('Amusez-vous bien !')
    text = '\n'.join(team_text)
    return text


def command_log(cmd):
    t = time.time()
    lt = time.ctime(t)
    print("{} | Receive command : {}".format(lt, cmd))


@dp.message_handler(commands=['start'])
async def welcome(message: types.Message):
    command_log("start")
    id_chat = message.chat.id
    text = "Hello ! Je suis MintBuilder ! \n" \
           "Je m'occupe de créer des sondages pour organiser des quiz et de tirer les équipes.\n" \
           "Je peux créer un sondage avec la commande /poll et je peux tirer les équipes avec la commande /team. " \
           "Pour plus de détails, vous pouvez utiliser la commande /help.\n" \
           "Amusez-vous bien !"
    await bot.send_message(chat_id=id_chat, text=text)


@dp.message_handler(commands=['poll'])
async def create_poll(message: types.Message):
    command_log("poll")
    id_chat = message.chat.id
    # Remove old poll if any
    if id_chat in polls:
        old_poll = polls[id_chat]
        await bot.stop_poll(chat_id=id_chat, message_id=old_poll[1])
        participants_per_poll.pop(old_poll[0])

    # Create new poll
    poll = await bot.send_poll(
        chat_id=id_chat,
        question='Prochain quiz, qui vient ?',
        options=['Let\'s go \U0001F44D !', 'Non... \U0001F614', "J'organise \U0001F60E !"],
        is_anonymous=False)
    # Save IDs of the poll and the chat
    id_poll = poll.poll.id
    polls[id_chat] = (id_poll, poll.message_id)
    participants_per_poll[id_poll] = []


@dp.poll_answer_handler()
async def handle_poll_answer(poll_answer):
    lt = time.ctime(time.time())
    print("{} | Receive poll answer".format(lt))
    id_poll = poll_answer["poll_id"]
    if id_poll in participants_per_poll:
        user_fn = poll_answer.user.first_name
        user_ln = poll_answer.user.last_name
        if user_ln == "None":
            user_ln = NO_NAME
        parse_fn = user_fn.split(' ')
        # If user has more than one first name registered, only keep the first "first name"
        # So if user_fn = "John William", only "John" is saved
        if len(parse_fn) > 1:
            user_fn = parse_fn[0]
        option = poll_answer.option_ids
        # If first option is chosen (meaning the user is coming)
        if option == [0]:
            participants_per_poll[id_poll].append((user_fn, user_ln))
            # Warning if the threshold is reach (usually 12)
            if len(participants_per_poll[id_poll]) == WARNING_THRESHOLD:
                for id_chat in [id for id in polls.keys() if polls[id][0] == id_poll]:
                    await bot.send_message(
                        chat_id=id_chat,
                        reply_to_message_id=polls[id_chat][1],
                        text="Attention, il y a maintenant {} personnes qui viennent".format(WARNING_THRESHOLD))
        # If user retract from coming
        elif option == [] and (user_fn, user_ln) in participants_per_poll[id_poll]:
            participants_per_poll[id_poll].remove((user_fn, user_ln))
    else:
        print("Warning : Unregistered poll answered")


@dp.message_handler(commands=['add'])
async def add_teammate(message: types.Message):
    command_log('add')
    id_chat = message.chat.id
    parse_text = message.text.split(' ')
    if len(parse_text) < 2:
        await message.reply("Personne à ajouter")
    else:
        user = parse_text[1:]
        if len(user) > 1:
            teammate = (user[0], " ".join(user[1:]))
        else:
            teammate = (user[0], NO_NAME)
        try:
            if teammate not in participants_per_poll[polls[id_chat][0]]:
                participants_per_poll[polls[id_chat][0]].append(teammate)
                # Warning if the threshold is reach (usually 12)
                if len(participants_per_poll[polls[id_chat][0]]) == WARNING_THRESHOLD:
                    await bot.send_message(
                        chat_id=id_chat,
                        reply_to_message_id=polls[id_chat][1],
                        text="Attention, il y a maintenant {} personnes qui viennent".format(WARNING_THRESHOLD))
            else:
                await message.reply("{} participe déjà !".format(teammate[0]))
        except KeyError:
            await message.reply(text="Aucun sondage actif auquel ajouter {}".format(teammate[0]))


@dp.message_handler(commands=['remove'])
async def remove_teammate(message: types.message):
    command_log('remove')
    id_chat = message.chat.id
    parse_text = message.text.split(' ')
    if len(parse_text) < 2:
        await message.reply("Personne à retirer")
    else:
        user = parse_text[1:]
        if len(user) > 1:
            teammate = (user[0], " ".join(user[1:]))
        else:
            last_name = NO_NAME
            counter = 0
            for u in participants_per_poll[polls[id_chat][0]]:
                if u[0] == user[0]:
                    last_name = u[1]
                    counter += 1
            teammate = (user[0], last_name)
            if counter > 1:
                await bot.send_message(
                    chat_id=id_chat,
                    text="Il y a plusieurs {} qui ont répondu ! Merci de préciser un nom de famille".format(teammate[0]))
        try:
            if teammate in participants_per_poll[polls[id_chat][0]]:
                participants_per_poll[polls[id_chat][0]].remove(teammate)
            else:
                await bot.send_message(
                    chat_id=id_chat,
                    text="{} ne venait déjà pas !".format(teammate[0]))
        except KeyError:
            await message.reply(text="Aucun sondage actif auquel retirer {}".format(teammate[0]))


@dp.message_handler(commands=['participants'])
async def participant_list(message: types.Message):
    command_log("participants")
    id_chat = message.chat.id
    try:
        id_poll = polls[id_chat][0]
    except KeyError:
        await message.reply(text="Aucun sondage actif pour voir les participants")
    else:
        participants = ["Il y a actuellement {} personnes qui viennent \U0001F44D \n"
                        "\n*Liste des participant-e-s*".format(len(participants_per_poll[id_poll]))]
        if homonym_check(participants_per_poll[id_poll]):
            for i in participants_per_poll[id_poll]:
                participants.append("- {} {}".format(i[0], i[1]))
        else:
            for i in participants_per_poll[id_poll]:
                participants.append("- {}".format(i[0]))
        text_to_send = '\n'.join(participants)
        await bot.send_message(
            chat_id=id_chat,
            reply_to_message_id=polls[id_chat][1],
            text=text_to_send,
            parse_mode='Markdown')


@dp.message_handler(commands=['team'])
async def create_team(message: types.Message):
    command_log("team")
    id_chat = message.chat.id
    try:
        id_poll = polls[id_chat][0]
    except KeyError:
        await message.reply(text="Aucun sondage actif pour créer les équipes")
    else:
        participants = participants_per_poll[id_poll]
        if len(participants) < 1:
            await bot.send_message(chat_id=id_chat, text="Il n'y a aucun participant...")
        else:
            # Create constraints from arguements
            constraints = []
            command = message.text
            next_space = command.find(' ')
            counter = 0
            while next_space > 0 and counter < 20:
                begin_cons = command.find('(', next_space) + 1
                end_cons = command.find(')', next_space)
                raw_cons = command[begin_cons: end_cons].split(',')
                cons_to_add = []
                for cons in raw_cons:
                    cons = cons.strip()
                    parse_con = cons.split(' ')
                    if len(parse_con) > 1:
                        cons_to_add.append((parse_con[0], ' '.join(parse_con[1:])))
                    else:
                        cons_to_add.append((parse_con[0], NO_NAME))
                constraints.append(cons_to_add)
                next_space = command.find('(', end_cons)
                counter += 1
            # Remove constraints that are not participants
            constraints_complete = []
            enough_info = True
            for cons in constraints:
                cons_complete = []
                for p in cons:
                    for u in participants:
                        if p[0] == u[0] and (p[1] == NO_NAME or p[1] == u[1]):
                            cons_complete.append(u)
                if len(cons_complete) != len(cons):
                    print(cons_complete)
                    enough_info = False
                constraints_complete.append(cons_complete)
            text_to_send = shuffle_with_constraints(participants, constraints_complete) if enough_info else \
                "Il n\'y a pas suffisamment d'information pour créer les équipes. " \
                "Il est probablement nécessaire d\'ajouter les noms de familles"
            await bot.send_message(
                chat_id=id_chat,
                text=text_to_send,
                parse_mode='Markdown')


@dp.message_handler(commands=['help'])
async def help_message(message: types.Message):
    command_log('help')
    id_chat = message.chat.id
    text = ["*Voici mes commandes :*", '- /start : Affiche un message d\'introduction',
            '- /poll : Crée un sondage à 3 réponses dont seule la première est positive',
            '- /add <nom> : Permet d\'ajouter un-e participant-e au prochain quiz. '
            'À n\'utiliser que si la personne n\'a pas telegram, sinon il est préférable de forwarder le sondage',
            '- /remove <nom> : Permet de retirer un-e participant-e du prochain quiz. '
            'À n\'utiliser que si la personne n\'a pas telegram, sinon il est préférable de retirer son vote du '
            'sondage.\n '
            '(Il faut appuyer sur l\'énoncé du sondage puis \"retract vote\")',
            '- /participants : Permet d\'afficher la liste des participant-e-s au prochain quiz',
            '- /team <(nom1, nom2)> : Génère aléatoirement des équipes avec maximum 6 membres. '
            'Il est possible de demander que plusieurs personnes soient dans la même équipe '
            'en les mettant entre parenthèses à la suite de la commande.', '\n*Exemples* :',
            '/add Alice - Alice (qui n\'a pas telegram) est ajoutée au prochain quiz',
            '/remove Alice - Alice (qui n\'a toujours pas telegram) est retirée du prochain quiz',
            '/team (Alice, Bob) - Alice et Bob seront dans la même équipe.',
            '/team (Alice, Bob, Charlie) - Alice, Bob et Charles seront dans la même équipe.',
            '/team (Alice, Bob) (Charlie, Dave) - '
            'Alice et Bob seront dans la même équipe et Charlie et Dave seront dans la même équipe.\n'
            '- /git : provide the link to the github (https://github.com/Risbobo/MintBuilderPublic)']
    text_to_send = '\n'.join(text)
    await bot.send_message(chat_id=id_chat, text=text_to_send, parse_mode='Markdown')


@dp.message_handler(commands=['debug'])
async def debug(message: types.Message):
    command_log('debug')
    print(polls)
    print(participants_per_poll)


@dp.message_handler(commands=['git'])
async def welcome(message: types.Message):
    command_log("git")
    id_chat = message.chat.id
    text = "[Link to GitHub](https://github.com/Risbobo/MintBuilderPublic)"
    await bot.send_message(chat_id=id_chat, text=text, parse_mode='Markdown')


@dp.message_handler(commands=['save'])
async def shutdown(message: types.Message):
    command_log('save')
    with open("config.txt", 'w') as file:
        file.write(str(polls) + '\n')
        file.write(str(participants_per_poll) + '\n')
        file.write(bot_token)


executor.start_polling(dp)
